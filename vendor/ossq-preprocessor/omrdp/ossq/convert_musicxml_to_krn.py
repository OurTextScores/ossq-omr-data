import time
import warnings
import subprocess
from pathlib import Path
import shutil
import argparse

from tqdm import tqdm

import converter21 as c21
from music21 import converter

from modules.lmxe.lmxe import linearize_lmxe, delinearize_lmxe
from modules.lmxe.lmxe.LMXEFile import LMXEFile, LMXEMetadata
from modules.lmxe.lmxe.symbolic.MxlFile import MusicXMLFile

from omrdp.utils import get_ts, get_argument_parser
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
from omrdp.utils import run_parallel
from omrdp.utils.symbolic import remove_time_signatures
from omrdp.utils.symbolic.musicxml import SHORT, compare_scores

warnings.filterwarnings('ignore', module='music21.*')
# register converter21's musicxml<->humdrum converter
c21.register()


def _convert_musicxml_to_krn(
  sq_dir, 
  pdf_type,  
  l_p, 
  x_p, 
  k_p, 
  verify
):
  # Suppress all warnings from music21
  warnings.filterwarnings('ignore', module='music21.*')
  # register converter21's musicxml<->humdrum converter
  import music21 as m21
  import converter21 as c21
  c21.register()
  
  delinearize_lmxe(l_p, force_inject_time=True).write(x_p)
  
  try:
    score = m21.converter.parse(
      x_p, 
      forceSource=True
    )
  except Exception as e:
    err = f"{k_p.stem:<20} {'None':>10}  {'None':>10}  {'CONVERSION':<16} {f'Parsing MusicXML: {e}':<}"
    raise RuntimeError(err)
  
  k_p_with_time = k_p.with_stem(f"{k_p.stem}_with_time")
  try:
    score.write('humdrum', k_p_with_time)
  except Exception as e:
    err = f"{k_p.stem:<20} {'None':>10}  {'None':>10}  {'CONVERSION':<16} {f'Writing krn : {e}':<}"
    raise RuntimeError(err)
  
  krn_str_with_time = k_p_with_time.read_text(encoding='utf-8')
  
  krn_str = remove_time_signatures(
    'krn',
    krn_str_with_time
  )
  k_p.write_text(krn_str, encoding='utf-8')
  
  if not verify:
    return
  
  temp_dir = sq_dir / 'temp'
  reconv_path = temp_dir / (k_p.stem + '_from_krn.musicxml')
  try:
    kern = m21.converter.parse(
      k_p_with_time, 
      forceSource=True
    )
  except Exception as e:
    err = f"{k_p.stem:<20} {'None':>10}  {'None':>10}  {'CONVERSION':<16} {f'Parsing krn: {e}':<}"
    raise RuntimeError(err)
  
  try:
    kern.write('musicxml', reconv_path)
  except Exception as e:
    err = f"{k_p.stem:<20} {'None':>10}  {'None':>10}  {'CONVERSION':<16} {f'Writing MusicXML: {e}':<}"
    raise RuntimeError(err)


def _convert_musicxml_to_krn_process(sq_dir, pdf_type, l_p, x_p, k_p, verify):
  try:
    _convert_musicxml_to_krn(sq_dir, pdf_type, l_p, x_p, k_p, verify)
    return l_p.stem, None
  except Exception as e:
    return l_p.stem, str(e)


def main(args:argparse.Namespace):
  prj_root = Path(args.base_dir)
  verify = bool(args.verify)
  tgt_score_list = args.list_path
  
  pdf_type = args.pdf_type
  enable_multi_process = bool(args.multi_process)
  
  errout = prj_root / 'logs' / f'musicxml_to_krn_{pdf_type}_{get_ts()}.log'
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
    sq_dir = body['path']
    
    sq_dir = score_dir / body['path']
    
    if pdf_type == 'scanned' and not (sq_dir / f'{sqid}_scanned.csv').exists():
      continue
    
    temp_dir = sq_dir / 'temp'
    temp_dir.mkdir(exist_ok=True)
    
    lmxe_dir = sq_dir / 'lmxe' / pdf_type / 'systemwise'
    lmxe_paths = lmxe_dir.glob(f'{sqid}*.lmxe')
    lmxe_paths = sorted(lmxe_paths)
    
    musicxml_dir = sq_dir / 'musicxml' / pdf_type / 'systemwise'
    
    krn_dir = sq_dir / 'krn' / pdf_type / 'systemwise'
    krn_dir.mkdir(parents=True, exist_ok=True)
    
    for l_p in tqdm(lmxe_paths, leave=False):
      task_list.append((
        sq_dir,
        pdf_type,
        l_p,
        musicxml_dir / (l_p.stem + '_with_time' + '.musicxml'),
        krn_dir / (l_p.stem + '.krn'),
        verify,
      ))
  
  if enable_multi_process:
    results = run_parallel(
      _convert_musicxml_to_krn_process, 
      task_list, 
      show_progress=True,
      progress_desc="Converting musicxml to krn (multi-process)"
    )
    for seg_id, err in results:
      if err is not None:
        with open(errout, 'a', encoding='utf-8') as f:
          print(err, file=f)
  else:
    pbar = tqdm(task_list, desc="Converting musicxml to krn")
    for sq_dir, pdf_type, l_p, x_p, k_p, verify in pbar:
      pbar.set_description(f"Converting musicxml to krn {l_p.stem}")
      seg_id, err = _convert_musicxml_to_krn_process(
        sq_dir, 
        pdf_type, 
        l_p, 
        x_p, 
        k_p, 
        verify
      )
      
      if err is not None:
        with open(errout, 'a', encoding='utf-8') as f:
          print(err, file=f)
  
  if not verify:
    return
  
  verify_task_list = [
    (
      x_p,
      sq_dir / 'temp' / f"{k_p.stem}_from_krn.musicxml",
    )
    for sq_dir, _, _, x_p, k_p, _ in tqdm(task_list, desc="Preparing verification tasks")
  ]
  
  time.sleep(2) # ensure all file operations are completed before verification
  
  results = compare_scores(
    task_list=verify_task_list,
    remove_stem_direction=False,
    enable_multi_process=enable_multi_process,
    is_lmx=False,
  )
  
  with open(errout, 'a', encoding='utf-8') as f:
    for i, (gt_path, pred_path) in enumerate(verify_task_list):
      res, err = results[i]
      
      seg_id = gt_path.stem.replace('_with_time', '')
      
      if err is not None:
        print(
          f'{str(err)}', 
          file=f
        )
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