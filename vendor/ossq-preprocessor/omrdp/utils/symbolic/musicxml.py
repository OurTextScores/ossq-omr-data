import warnings
import copy
import difflib
from fractions import Fraction
from pathlib import Path
import shutil

import xml.etree.ElementTree as ET

from tqdm.auto import tqdm

import musicdiff as md
from musicdiff.detaillevel import DetailLevel

from modules.lmxe.lmxe.symbolic.MxlFile import MusicXMLFile

from omrdp.utils import run_parallel

warnings.filterwarnings('ignore', module='music21.*')


SHORT = lambda k: k.replace(' OMR-ED', '').replace('wrong ', '').replace('entire ', '')


FALSE_POSITIVE_CATEGORIES = frozenset({
  'wrong timesig OMR-ED',
  'wrong tuplet OMR-ED',
})


def _normalize_pred_divisions(
  gt:MusicXMLFile, 
  pred:MusicXMLFile
) -> MusicXMLFile:
  """Rewrite pred_path → out_path with <duration> values re-expressed in GT's
  <divisions> scale (rounded to nearest integer, same as MuseScore does).

  MuseScore exports MusicXML with divisions=480, which cannot exactly represent
  some tuplet durations (e.g. 13:8 → 480/13 ≈ 36.923, stored as 37).  The LMX
  delinearizer may choose a higher-precision divisions (e.g. 1560) that CAN
  represent the value exactly (1560/13 = 120).  MusicDiff then sees 37/480 ≠
  120/1560 and counts every such note as an error, even though they encode the
  same musical duration to within MuseScore's rounding.

  After normalisation every pred duration that would round to the same integer
  as the GT duration (at GT's precision) compares equal, so MusicDiff never
  sees the discrepancy.
  """
  # Collect GT's divisions value per measure (in document order).
  gt_div = 1
  gt_div_seq: list[int] = []
  for m in gt.tree.getroot().iter('measure'):
    attrs = m.find('attributes')
    if attrs is not None:
      d = attrs.findtext('divisions')
      if d:
        gt_div = int(d)
    gt_div_seq.append(gt_div)
  
  pred_div = 1
  for idx, m in enumerate(pred.tree.getroot().iter('measure')):
    attrs = m.find('attributes')
    if attrs is not None:
      d = attrs.findtext('divisions')
      if d:
        pred_div = int(d)

    if idx >= len(gt_div_seq):
      continue  # pred has more measures than GT — leave as-is

    target_div = gt_div_seq[idx]
    if target_div == pred_div:
      continue  # already same scale

    # Rescale <divisions> declaration.
    if attrs is not None:
      divs_el = attrs.find('divisions')
      if divs_el is not None:
        divs_el.text = str(target_div)

    # Rescale every <duration> inside this measure (notes, forward, backup).
    for el in m.iter():
      if el.tag == 'duration' and el.text:
        new_dur = round(Fraction(int(el.text), pred_div) * target_div)
        el.text = str(new_dur)

  return pred



def compare_musicxml(
  *,
  pred_path:Path,
  gt_path:Path,
  is_lmx:bool=False,
  ignore_stem_direction:bool=False,
):
  """
  Pre-processes pred before running MusicDiff to eliminate systematic formatting
  differences introduced by the LMX round-trip that are not real musical errors:

  - Slur number normalization (_strip_slur_numbers):
    The LMX delinearizer assigns explicit number="1", number="2", … to
    concurrent slurs; cleaned source files always use number="".  Stripping
    the attribute from pred before comparison eliminates both the direct
    'wrong slur OMR-ED' false positive and its cascade: when a short measure
    contains nested slurs the accumulated per-note mismatch cost can exceed
    MusicDiff's insert+delete threshold, causing the whole measure to be
    flagged as 'entire measure insert/delete OMR-ED' even though pitches and
    durations are identical.

  - Tuplet duration rounding (_normalize_pred_divisions):
    MuseScore exports divisions=480, which cannot represent all tuplet
    durations exactly (e.g. 13:8 → 480/13 ≈ 36.923 → stored as 37).
    The LMX delinearizer may use a finer divisions that stores the exact
    rational, making MusicDiff see a tiny but non-zero difference on every
    such note.  pred is normalised in-place to GT's divisions before
    comparison so these cancel out.

  Remaining false positive categories (post-normalisation, classified via
  FALSE_POSITIVE_CATEGORIES):
  - 'wrong timesig OMR-ED':
    LMX drops print-object="no" from courtesy/hidden time sigs.
    The time-signature value is identical.
  - 'wrong tuplet OMR-ED':
    For whole-note-per-measure tuplets, LMX emits
    <tuplet type="stop"/> before <tuplet type="start"/> on the same note,
    reversing the order vs. the original.  Both sides encode the same grouping.
  """
  warnings.filterwarnings('ignore', module='music21.*')
  
  if is_lmx:
    gt = MusicXMLFile.load_musicxml(gt_path)
    pred = MusicXMLFile.load_musicxml(pred_path)
    pred.remove_zero_alters()
    pred.strip_slur_numbers()
    pred = _normalize_pred_divisions(gt, pred)
    pred.write(pred_path)
  
  metrics = md._diff_omr_ned_metrics(
    predpath=pred_path, 
    gtpath=gt_path,
    detail=DetailLevel.Default
  )
  if metrics is None:
    return None

  total_numsyms = metrics.gt_numsyms + metrics.pred_numsyms
  
  fp_categories = set(FALSE_POSITIVE_CATEGORIES)
  if is_lmx and ignore_stem_direction:
    fp_categories.add("wrong note stem OMR-ED")

  fp = {
    k: int(v)
    for k, v in metrics.edit_distances_dict.items() 
    if k in fp_categories and v > 0
  }
  real = {
    k: int(v)
    for k, v in metrics.edit_distances_dict.items()
    if k not in fp_categories and v > 0
  }
  real_ned = (
    sum(real.values()) / total_numsyms
    if total_numsyms > 0
    else 0.0
  )

  return dict(
    raw_ned=metrics.omr_ned, 
    real_ned=real_ned,
    has_real_errors=bool(real), 
    real_errors=real, 
    fp_errors=fp,
  )


def _compare_scores_process(i, gt, pred, remove_stem_direction, is_lmx):
  try:
    res = compare_musicxml(
      pred_path=pred,
      gt_path=gt,
      is_lmx=is_lmx,
      ignore_stem_direction=remove_stem_direction,
    )
    return i, res, None
  except Exception as e:
    return i, None, e


def compare_scores(
  task_list:list[tuple[Path,Path]], 
  remove_stem_direction:bool, 
  enable_multi_process:bool,
  is_lmx:bool=False,
):
  results = {}
  args_list = [
    (i, orig, delin, remove_stem_direction, is_lmx) 
    for i, (orig, delin) in enumerate(task_list)
  ]
  if enable_multi_process:
    for i, res, err in run_parallel(
      _compare_scores_process, 
      args_list, 
      show_progress=True,
      progress_desc="Comparing scores"
    ):
      results[i] = (res, err)
  else:
    for args in tqdm(args_list, desc="Comparing scores", dynamic_ncols=True):
      i, res, err = _compare_scores_process(*args)
      results[i] = (res, err)
  
  return results


def annotate_musicxmls(exceptions, dataset_score_dir):
  annotated_musicxmls = []
  
  for exception in tqdm(exceptions, dynamic_ncols=True):
    *_, (src_musicxml, tgt_musicxml) = exception
    
    if not src_musicxml.exists() or not tgt_musicxml.exists():
      print(f"MusicXML files not found for exception: {src_musicxml.parent.relative_to(dataset_score_dir)}")
    
    pairs = [
      src_musicxml,
      tgt_musicxml, 
    ]
    
    src_musicxml_ann = shutil.copy(
      src_musicxml, 
      src_musicxml.with_name(f"{src_musicxml.stem}_ann{src_musicxml.suffix}")
    )
    tgt_musicxml_ann = shutil.copy(
      tgt_musicxml,
      tgt_musicxml.with_name(f"{tgt_musicxml.stem}_ann{tgt_musicxml.suffix}")
    )
    
    md.diff(
      src_musicxml_ann,
      tgt_musicxml_ann,
      out_path1=src_musicxml_ann.with_suffix('.pdf'),
      out_path2=tgt_musicxml_ann.with_suffix('.pdf'),
      force_parse=True,
    )
    
    pairs.append(src_musicxml_ann)
    pairs.append(tgt_musicxml_ann)
    
    annotated_musicxmls.append(pairs)
  
  return annotated_musicxmls


def parse_annotated_errors(annotated_path):
  """
  Parse a MusicDiff-annotated MusicXML file and return the list of error annotations.

  MusicDiff marks each error with:
    <direction><direction-type>
      <words color="#FF0000">label</words>
    </direction-type></direction>
  immediately before the colored element it refers to, inside the same <measure>.

  Returns:
    list of dicts:  {'measure': str, 'error_type': str, 'element_tag': str}
    in document order.
  """
  tree = ET.parse(annotated_path)
  
  errors = []
  for measure in tree.getroot().iter('measure'):
    mnum = measure.get('number', '?')
    children = list(measure)
    
    for i, child in enumerate(children):
      if child.tag != 'direction':
        continue
      
      dt = child.find('direction-type')
      if dt is None:
        continue
      
      words = dt.find('words')
      if words is None or words.get('color') != '#FF0000':
        continue
      
      label = (words.text or '').strip()
      if not label:
        continue
      
      # find the first colored sibling that follows this direction
      elem_tag = ''
      for j in range(i + 1, len(children)):
        c = children[j]
        if c.get('color') == '#FF0000':
          elem_tag = c.tag
          break
      
      errors.append({'measure': mnum, 'error_type': label, 'element_tag': elem_tag})
  
  return errors


_ANSI_RED   = '\033[31m'
_ANSI_GREEN = '\033[32m'
_ANSI_CYAN  = '\033[36m'
_ANSI_RESET = '\033[0m'


def inspect_error(error, src_path, tgt_path, context=0, diff=True):
  """
  Print the MusicXML measure context around an error for manual inspection.

  Args:
    error    : dict from parse_annotated_errors() — needs 'measure' and 'error_type'
    src_path : path to original cleaned MusicXML
    tgt_path : path to delinearized MusicXML
    context  : number of surrounding measures to show on each side (default 1)
    diff     : 
      if True (default), show a unified diff (git-diff style) between
      src and tgt for each context measure; if False, show the two files
      side-by-side (original then reconstructed).
  """
  mnum  = str(error['measure'])
  etype = error['error_type']
  etag  = error.get('element_tag', '')

  print(f"{'='*65}")
  print(f"Error    : {etype}" + (f" ({etag})" if etag else ""))
  print(f"Measure  : {mnum}")
  print(f"{'='*65}")

  def _load_measures(p):
    tree = ET.parse(p)
    measures = list(tree.getroot().iter('measure'))
    order = [m.get('number', str(i)) for i, m in enumerate(measures)]
    by_num = {n: m for n, m in zip(order, measures)}
    return order, by_num

  def _fmt(m):
    m = copy.deepcopy(m)
    ET.indent(m, space='  ')
    s = ET.tostring(m, encoding='unicode')
    # strip outer <measure ...>...</measure> wrapper so we control the header line
    inner = s[s.index('>')+1 : s.rindex('<')]
    return inner

  if diff:
    src_order, src_by_num = _load_measures(src_path)
    tgt_order, tgt_by_num = _load_measures(tgt_path)

    if mnum not in src_by_num:
      print(f"  [measure {mnum} not found in {Path(src_path).name}]")
      return

    idx   = src_order.index(mnum)
    start = max(0, idx - context)
    end   = min(len(src_order), idx + context + 1)

    print(f"{_ANSI_RED}--- original (cleaned){_ANSI_RESET}")
    print(f"{_ANSI_GREEN}+++ reconstructed (delin){_ANSI_RESET}")

    for n in src_order[start:end]:
      marker = '  <<<' if n == mnum else ''
      src_lines = _fmt(src_by_num[n]).splitlines() if n in src_by_num else []
      tgt_lines = _fmt(tgt_by_num[n]).splitlines() if n in tgt_by_num else []

      header = f'<measure number="{n}">{marker}'
      src_full = [header] + src_lines + ['</measure>']
      tgt_full = [header] + tgt_lines + ['</measure>']

      diff_lines = list(difflib.unified_diff(
        src_full, tgt_full,
        fromfile=f'measure {n} (src)',
        tofile=f'measure {n} (tgt)',
        lineterm='',
        n=max(len(src_full), len(tgt_full)),  # show full measure as context
      ))

      if not diff_lines:
        # identical — print compactly
        print(f"\n{header}")
        for l in src_lines:
          print(f"  {l}")
        print('</measure>')
        continue

      print()
      for line in diff_lines:
        if line.startswith('---') or line.startswith('+++'):
          print(f"{_ANSI_CYAN}{line}{_ANSI_RESET}")
        elif line.startswith('-'):
          print(f"{_ANSI_RED}{line}{_ANSI_RESET}")
        elif line.startswith('+'):
          print(f"{_ANSI_GREEN}{line}{_ANSI_RESET}")
        elif line.startswith('@@'):
          print(f"{_ANSI_CYAN}{line}{_ANSI_RESET}")
        else:
          print(line)

  else:
    for label, p in [
      ('ORIGINAL  (cleaned)', src_path),
      ('RECONSTRUCTED (delin)', tgt_path)
    ]:
      order, by_num = _load_measures(p)

      print(f"\n{'─'*65}")
      print(f"  {label}")
      print(f"{'─'*65}")

      if mnum not in by_num:
        print(f"  [measure {mnum} not found in {Path(p).name}]")
        continue

      idx   = order.index(mnum)
      start = max(0, idx - context)
      end   = min(len(order), idx + context + 1)

      for n in order[start:end]:
        marker = '  <<<' if n == mnum else ''
        print(f"\n<measure number=\"{n}\">{marker}")
        print(_fmt(by_num[n]))
        print('</measure>')
