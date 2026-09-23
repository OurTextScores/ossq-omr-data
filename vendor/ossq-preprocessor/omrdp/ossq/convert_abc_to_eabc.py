import time
import warnings
from pathlib import Path
import argparse

from tqdm import tqdm

from music21 import converter
import converter21 as c21

from omrdp.utils import get_ts, get_argument_parser
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
from omrdp.utils import run_parallel

from omrdp.utils.symbolic.musicxml import SHORT, compare_scores
from omrdp.utils.symbolic.abc import abc_to_eabc, eabc_to_abc

# Suppress all warnings from music21
warnings.filterwarnings('ignore', module='music21.*')
# register converter21's musicxml<->abc converter
c21.register()


def _convert_abc_to_eabc(
  a_p:Path,
  ea_p:Path,
  reconv_path:Path,
  verify:bool,
):
  if not a_p.exists():
    err = f"{a_p.stem:<20} {'None':>10}  {'None':>10}  {'FAILED':<16} ABC file not found"
    raise FileNotFoundError(err)

  abc = a_p.read_text(encoding='utf-8')
  
  if abc.strip() == '':
    err = f"{a_p.stem:<20} {'None':>10}  {'None':>10}  {'FAILED':<16} ABC file is empty"
    raise ValueError(err)
  
  eabc = abc_to_eabc(abc)
  ea_p.write_text(eabc, encoding='utf-8')
  
  if not verify:
    return
  
  abc_reconv = eabc_to_abc(eabc)
  reconv_path.write_text(abc_reconv, encoding='utf-8')


def _convert_abc_to_eabc_process(*args):
  try:
    _convert_abc_to_eabc(*args)
    return args[0].stem, None
  except Exception as e:
    return None, e


def main(args:argparse.Namespace):
  prj_root = Path(args.base_dir)
  verify = bool(args.verify)
  tgt_score_list = args.list_path
  level = args.level
  
  pdf_type = args.pdf_type
  enable_multi_process = bool(args.multi_process)
  
  errout = prj_root / 'logs' / f'abc_to_eabc_{pdf_type}_{level}_{get_ts()}.log'
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
    
    abc_paths = abc_dir.glob(f'{sqid}*.abc')
    abc_paths = sorted(abc_paths)
    
    for a_p in tqdm(abc_paths, leave=False):
      ea_p = a_p.with_suffix('.eabc')
      reconv_path = temp_dir / (ea_p.stem + '_from_eabc.abc')
      
      task_list.append((
        a_p,
        ea_p,
        reconv_path,
        verify,
      ))
  
  if enable_multi_process:
    results = run_parallel(
      _convert_abc_to_eabc_process, 
      task_list,
      show_progress=True,
      progress_desc="Converting ABC to EABC (multi-process)",
    )
    for seg_id, err in results:
      if err is not None:
        with open(errout, 'a', encoding='utf-8') as f:
          print(err, file=f)
  else:
    pbar = tqdm(task_list, desc="Converting ABC to EABC")
    for args in pbar:
      pbar.set_description(f"Converting ABC to EABC {args[0].stem}")
      seg_id, err = _convert_abc_to_eabc_process(*args)
      if err is not None:
        with open(errout, 'a', encoding='utf-8') as f:
          print(err, file=f)
  
  if not verify:
    return
  
  
  verify_task_list = [
    (a_p, reconv_path)
    for a_p, ea_p, reconv_path, _ in tqdm(task_list, desc="Preparing verification tasks")
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
      
      seg_id = gt_path.stem
      
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
    default='systemwise', 
    choices=['systemwise', 'partwise'], 
    required=True,
  )
  
  args = parser.parse_args()

  main(args)