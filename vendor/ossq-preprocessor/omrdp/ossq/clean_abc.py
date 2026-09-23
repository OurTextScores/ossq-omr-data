import time
import warnings
import argparse
from pathlib import Path
import re
import shutil

from tqdm import tqdm

import converter21 as c21
import musicdiff as md

from omrdp.utils import get_argument_parser, get_ts
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
from omrdp.utils import run_parallel

from omrdp.utils.symbolic.musicxml import SHORT, compare_musicxml, compare_scores

# Suppress all warnings from music21
warnings.filterwarnings('ignore', module='music21.*')
# register converter21's musicxml<->abc converter
c21.register()

# Header fields to drop entirely
_DROP_FIELDS = {'X', 'T', 'I'}

# Matches nm="..." attribute in V: lines (with any leading whitespace)
_NM_RE = re.compile(r'\s*nm="[^"]*"')

# Matches a trailing bar-count comment: | %<digits> at end of line.
# Uses [ \t]* instead of \s* to avoid consuming the newline character.
_BAR_COUNT_RE = re.compile(r'(\|)[ \t]*%\d+[ \t]*$', re.MULTILINE)


def clean_abc(text: str) -> str:
  """
  Apply all cleaning rules to the content of a single .abc file.

  Rules:
    1. Drop following Information fields
      - X:
      - T:
      - I:
    2. Remove nm="..." from V: fields.
    3. Remove trailing `%<N>` bar-count comments, keeping the |.
  """
  lines = text.splitlines(keepends=True)
  
  out = []
  for line in lines:
    # information fields: 
    # single letter + colon at start
    if len(line) >= 2 and line[1] == ':' and line[0].isalpha():
      field = line[0].upper()
      if field in _DROP_FIELDS:
        continue
      if field == 'V':
        line = _NM_RE.sub('', line)
    
    # tune body: 
    # strip trailing bar-count comment
    else:
      line = _BAR_COUNT_RE.sub(r'\1', line)
    
    out.append(line)
  
  return ''.join(out)


def _clean_abc_files(
  abc_path:list[Path],
  tgt_dir:Path,
):
  try:
    text = abc_path.read_text(encoding='utf-8')
    cleaned = clean_abc(text)
    
    cleaned_abc_path = tgt_dir / abc_path.name
    cleaned_abc_path.write_text(cleaned, encoding='utf-8')
  
  except Exception as e:
    err = f"{abc_path.stem:<20} {'None':>10}  {'None':>10}  {'FAILED':<16} {f'Cleaning abc: {e}':<}"
    raise RuntimeError(err)


def _clean_abc_files_process(*args):
  try:
    _clean_abc_files(*args)
    return args[0].stem, None
  except Exception as e:
    return None, e


def main(args: argparse.Namespace):
  prj_root = Path(args.base_dir)
  tgt_score_list = args.list_path
  pdf_type = args.pdf_type
  level = args.level
  
  verify = bool(args.verify)
  enable_multi_process = bool(args.multi_process)
  
  errout = prj_root / 'logs' / f'clean_abc_{pdf_type}_{level}_{get_ts()}.log'
  with open(errout, 'a', encoding='utf-8') as f:
    print(
      f"{'Seg ID':<20} {'Raw NED':>10}  {'Real NED':>10}  {'Verdict':<16} Details", 
      file=f
    )
    print('-' * 95, file=f)

  data_dir = prj_root / 'data'
  score_dir = prj_root / 'scores'

  if tgt_score_list:
    data = load_ossq_score_list(tgt_score_list)
  else:
    data = load_ossq_metadata(data_dir / 'scores.yaml')
  
  data = list(data.items())
  
  task_list = []
  for score_id, body in tqdm(data, desc="Preparing tasks"):
    sqid = body['sqid']
    sq_dir = score_dir / body['path']
    
    if pdf_type == 'scanned' and not (sq_dir / f'{sqid}_scanned.csv').exists():
      continue
    
    temp_dir = sq_dir / 'temp'
    temp_dir.mkdir(exist_ok=True)
    
    abc_dir = sq_dir / 'abc' / pdf_type / level
    
    uncleaned_dir = abc_dir / 'uncleaned'
    uncleaned_dir.mkdir(exist_ok=True)
    
    tgt_dir = abc_dir 
    if level == 'partwise':
      tgt_dir = abc_dir / 'unaligned'
    tgt_dir.mkdir(exist_ok=True)
    
    abc_paths = uncleaned_dir.glob('*.abc')
    abc_paths = sorted(abc_paths)
    
    for abc_path in abc_paths:
      if '_with_time' in abc_path.stem:
        continue
      
      task_list.append((
        abc_path,
        tgt_dir,
      ))
  
  if enable_multi_process:
    results = run_parallel(
      _clean_abc_files_process,
      task_list,
      show_progress=True,
      progress_desc="Cleaning abc files (multi-process)",
    )
    for seg_id, err in results:
      if err is not None:
        with open(errout, 'a', encoding='utf-8') as f:
          print(err, file=f)
  else:
    pbar = tqdm(task_list, desc="Cleaning abc files")
    for args in pbar:
      pbar.set_description(f"Cleaning abc {args[0].stem}")
      seg_id, err = _clean_abc_files_process(*args)
      if err is not None:
        with open(errout, 'a', encoding='utf-8') as f:
          print(err, file=f)
  
  if not verify:
    return
  
  verify_task_list = [
    (
      abc_path,
      tgt_dir / abc_path.name
    )
    for abc_path, tgt_dir in tqdm(task_list, desc="Preparing verification tasks")
  ]
  
  time.sleep(2) # ensure all file operations are completed before verification
  
  results = compare_scores(
    verify_task_list,
    remove_stem_direction=False,
    enable_multi_process=enable_multi_process,
    is_lmx=False,
  )
  
  with open(errout, 'a', encoding='utf-8') as f:
    for i, (gt_path, pred_path) in enumerate(verify_task_list):
      res, err = results[i]
      
      seg_id = pred_path.stem
      
      if err is not None:
        print(err, file=f)
        continue
      
      if res is None:
        print(
          f"{seg_id:<20} {'None':>10}  {'None':>10}  {'FAILED':<16} {'MusicDiff returned None':<}",
          file=f
        )
        continue
      
      verdict = 'success'
      
      if res['has_real_errors']:
        verdict = 'TRUE POSITIVE'
        
      elif res['raw_ned'] > 0:
        verdict = 'false positive'
      
      real_str = ', '.join(f"{SHORT(k)}: {v}" for k, v in res['real_errors'].items())
      fp_str = ', '.join(f"{SHORT(k)}: {v}" for k, v in res['fp_errors'].items())
      detail = real_str if real_str else f"[fp only: {fp_str}]"
      
      if verdict == 'success':
        detail = '👍'
      
      print(
        f"{seg_id:<20} {res['raw_ned']:>10.6f}  {res['real_ned']:>10.6f}  {verdict:<16} {detail}",
        file=f
      )


if __name__ == '__main__':
  parser = get_argument_parser()
  parser.add_argument(
    '--level',
    type=str,
    choices=['systemwise', 'partwise'],
    required=True,
    help='Level of abc files to clean.'
  )
  args = parser.parse_args()
  main(args)
