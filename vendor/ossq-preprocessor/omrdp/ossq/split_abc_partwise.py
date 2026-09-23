import time
import warnings
import shutil
from pathlib import Path
import argparse

from tqdm import tqdm

import music21 as m21
import converter21 as c21
from converter21.abc.xml2abc import vertaal as convertMusicXMLToABC

from modules.lmxe.lmxe import delinearize_lmxe
from modules.lmxe.lmxe.symbolic.MxlFile import MusicXMLFile
from modules.lmxe.lmxe.symbolic.part_to_score import parts_to_score

from omrdp.utils import get_argument_parser, get_ts
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
from omrdp.utils import run_parallel
from omrdp.utils.symbolic import remove_time_signatures
from omrdp.utils.symbolic.musicxml import SHORT, compare_scores

# Suppress all warnings from music21
warnings.filterwarnings('ignore', module='music21.*')
# register converter21's musicxml<->abc converter
c21.register()


def _split_partwise(
  sq_dir:Path,
  l_p:Path,
  x_p:Path,
  partwise_musicxml_dir:Path,
  partwise_abc_dir:Path,
  pdf_type:str,
  verify:bool
):
  if x_p.exists():
    musicxml = MusicXMLFile.load_musicxml(x_p)
  else:
    musicxml = delinearize_lmxe(l_p, force_inject_time=True)
    musicxml.write(x_p)
  
  parts = musicxml.get_parts()
  parts = parts['multi']
  
  for part_idx, (part_id, part_el) in enumerate(parts):
    seg_id = x_p.stem.replace('_with_time', '')
    seg_id = f"{seg_id}:{part_idx+1}"
    
    pw_x_p = partwise_musicxml_dir / f'{seg_id}_with_time.musicxml'
    a_p_with_time = partwise_abc_dir / f'{seg_id}_with_time.abc'
    a_p = partwise_abc_dir / f'{seg_id}.abc'
    
    temp_dir = sq_dir / 'temp'
    reconv_path = temp_dir / f"{seg_id}_from_abc.musicxml"
    
    part_musicxml = parts_to_score(
      [('multi', part_el)], 
    )
    part_musicxml = MusicXMLFile(part_musicxml)
    part_musicxml.strip_musicxml()
    
    part_musicxml.write(pw_x_p)
    
    try:
      abc_str_with_time, _ = convertMusicXMLToABC(str(part_musicxml), d=8, wev=1)
    except Exception as e:
      err = f"{seg_id:<20} {'None':>10}  {'None':>10}  {'FAILED':<16} {f'Converting abc: {e}':<}"
      raise RuntimeError(err)
    
    try:
      a_p_with_time.write_text(abc_str_with_time, encoding='utf-8')
    except Exception as e:
      err = f"{seg_id:<20} {'None':>10}  {'None':>10}  {'FAILED':<16} {f'Writing abc : {e}':<}"
      raise RuntimeError(err)
    
    abc_str = remove_time_signatures(
      'abc',
      abc_str_with_time,
    )
    a_p.write_text(abc_str, encoding='utf-8')
    
    if not verify:
      continue
    
    try:
      abc = m21.converter.parse(
        a_p_with_time, 
        forceSource=True
      )
    except Exception as e:
      err = f"{seg_id:<20} {'None':>10}  {'None':>10}  {'FAILED':<16} {f'Parsing abc: {e}':<}"
      raise RuntimeError(err)

    try:
      abc.write('musicxml', reconv_path)
    except Exception as e:
      err = f"{seg_id:<20} {'None':>10}  {'None':>10}  {'FAILED':<16} {f'Writing MusicXML: {e}':<}"
      raise RuntimeError(err)


def _split_partwise_process(*args):
  try:
    _split_partwise(*args)
    return args[1].stem, None
  except Exception as e:
    return None, e


def main(args:argparse.Namespace):
  prj_root = Path(args.base_dir)
  verify = bool(args.verify)
  tgt_score_list = args.list_path
  
  pdf_type = args.pdf_type
  enable_multi_process = bool(args.multi_process)

  errout = prj_root / 'logs' / f'split_abc_partwise_{pdf_type}_{get_ts()}.log'
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
    if temp_dir.exists():
      shutil.rmtree(temp_dir)
    temp_dir.mkdir(exist_ok=True)
    
    lmxe_dir = sq_dir / 'lmxe' / pdf_type / 'systemwise'
    lmxe_paths = lmxe_dir.glob(f"{sqid}*.lmxe")
    lmxe_paths = sorted(lmxe_paths)
    
    musicxml_dir = sq_dir / 'musicxml' / pdf_type / 'systemwise'
    
    partwise_musicxml_dir = sq_dir / 'musicxml' / pdf_type / 'partwise'
    partwise_musicxml_dir.mkdir(parents=True, exist_ok=True)
    
    partwise_abc_dir = sq_dir / 'abc' / pdf_type / 'partwise' / 'uncleaned'
    partwise_abc_dir.mkdir(parents=True, exist_ok=True)
    
    for l_p in tqdm(lmxe_paths, leave=False):
      x_p = musicxml_dir / f"{l_p.stem}_with_time.musicxml"
      
      task_list.append((
        sq_dir,
        l_p,
        x_p,
        partwise_musicxml_dir, 
        partwise_abc_dir, 
        pdf_type, 
        verify
      ))
  
  if enable_multi_process:
    results = run_parallel(
      _split_partwise_process, 
      task_list, 
      show_progress=True,
      progress_desc="Splitting abc (multi-process)"
    )
    for seg_id, err in results:
      if err is not None:
        with open(errout, 'a', encoding='utf-8') as f:
          print(err, file=f)
  else:
    pbar = tqdm(task_list, desc=f"Splitting abc {pdf_type}")
    for sq_dir, l_p, x_p, partwise_musicxml_dir, partwise_abc_dir, pdf_type, verify in pbar:
      seg_id = l_p.stem
      
      pbar.set_description(f"Splitting abc {pdf_type} {seg_id}")
      
      seg_id, err = _split_partwise_process(
        sq_dir,
        l_p,
        x_p,
        partwise_musicxml_dir,
        partwise_abc_dir,
        pdf_type,
        verify
      )
      if err is not None:
        with open(errout, 'a', encoding='utf-8') as f:
          print(err, file=f)
  
  if not verify:
    return
  
  verify_task_list = []
  for sq_dir, l_p, x_p, partwise_musicxml_dir, partwise_abc_dir, *_ in tqdm(task_list, desc="Preparing split abc verification tasks"):
    seg_id = l_p.stem
    
    pw_musicxml_paths = partwise_musicxml_dir.glob(f"{seg_id}*_with_time.musicxml")
    pw_musicxml_paths = sorted(pw_musicxml_paths)
    
    temp_dir = sq_dir / 'temp'
    for pw_x_p in pw_musicxml_paths:
      pw_seg_id = pw_x_p.stem.replace('_with_time', '')
      pw_a_p = partwise_abc_dir / f"{pw_seg_id}.abc"
      reconv_path = temp_dir / f"{pw_seg_id}_from_abc.musicxml"
      
      if pw_a_p.exists() and reconv_path.exists():
        reconv_path = temp_dir / f"{pw_seg_id}_from_abc.musicxml"
        verify_task_list.append((
          pw_x_p,
          reconv_path
        ))
  
  time.sleep(2) # ensure all file operations are completed before verification
  
  print(f"Verifying {len(verify_task_list)} partwise segments...")
  results = compare_scores(
    verify_task_list,
    remove_stem_direction=False,
    enable_multi_process=enable_multi_process,
    is_lmx=False,
  )
  
  with open(errout, 'a', encoding='utf-8') as f:
    for i, (gt_path, pred_path) in enumerate(verify_task_list):
      res, err = results[i]
      
      seg_id = gt_path.stem.replace('_with_time', '')
      
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
  args = parser.parse_args()

  main(args)