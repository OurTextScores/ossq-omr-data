import time
from pathlib import Path
import argparse

from tqdm import tqdm

from modules.lmxe.lmxe.LMXEFile import LMXEFile
from modules.lmxe.lmxe.LMXEFile import split_lmxe_partwise, merge_partwise_lmxes

from omrdp.utils import get_ts, get_argument_parser
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
from omrdp.utils import run_parallel


def _split_partwise(
  l_p,
  tgt_lmxe_dir,
  tgt_metadata_dir,
  verify,
):
  lmxe = LMXEFile.load(l_p, include_metadata=True)
  partwise_lmxes = split_lmxe_partwise(lmxe, include_metadata=True)
  
  for p_idx, part_lmxe in enumerate(partwise_lmxes):
    part_lmxe.write(
      tgt_lmxe_dir / f'{l_p.stem}:{p_idx+1}{l_p.suffix}',
      include_metadata=True,
    )
    part_lmxe.metadata.write(
      tgt_metadata_dir / f'{l_p.stem}:{p_idx+1}.yaml'
    )
  
  if not verify:
    return
  
  if not all( 
    p.metadata.measure_start == lmxe.metadata.measure_start 
    for p in partwise_lmxes
  ):
    err = f"{l_p.stem}: Measure start mismatch"
    raise RuntimeError(err)
  
  if not all( 
    p.metadata.measure_end == lmxe.metadata.measure_end 
    for p in partwise_lmxes
  ):
    err = f"{l_p.stem}: Measure end mismatch"
    raise RuntimeError(err)
  
  if not all( 
    p.metadata.measure_numbers == lmxe.metadata.measure_numbers
    for p in partwise_lmxes
  ):
    err = f"{l_p.stem}: Measure numbers mismatch"
    raise RuntimeError(err)
  
  merged = merge_partwise_lmxes(
    partwise_lmxes,
    include_metadata=True,
  )
  
  if lmxe.metadata.signature_injected != merged.metadata.signature_injected:
    err = f"{l_p.stem}: Signature injected mismatch"
    raise RuntimeError(err)
  
  if lmxe.metadata.signatures != merged.metadata.signatures:
    err = f"{l_p.stem}: Signatures mismatch"
    raise RuntimeError(err) 
  
  if lmxe != merged:
    err = f"{l_p.stem}: measures mismatch"
    raise RuntimeError(err)


def _split_partwise_process( 
  l_p,
  tgt_lmxe_dir,
  tgt_metadata_dir,
  verify,
):
  try:
    _split_partwise(
      l_p,
      tgt_lmxe_dir,
      tgt_metadata_dir,
      verify,
    )
    return l_p.stem, None
  except Exception as e:
    return l_p.stem, str(e)


def main(args:argparse.Namespace):
  prj_root = Path(args.base_dir)
  verify = bool(args.verify)
  pdf_type = args.pdf_type
  
  tgt_score_list = args.list_path
  enable_multi_process = bool(args.multi_process)

  errout = prj_root / 'logs' / f'split_lmxe_partwise_{pdf_type}_{get_ts()}.log'
  
  data_dir = prj_root / 'data'
  score_dir = prj_root / 'scores'
  
  if tgt_score_list:
    data = load_ossq_score_list(tgt_score_list)
  else:
    data = load_ossq_metadata(data_dir / 'scores.yaml')
  
  data = list(data.items())
  
  task_list = []
  for score_id, body in data:
    sqid = body['sqid']
    sq_dir = score_dir / body['path']
    
    if pdf_type == 'scanned' and not (sq_dir / f'{sqid}_scanned.csv').exists():
      continue
    
    temp_dir = sq_dir / 'temp'
    temp_dir.mkdir(exist_ok=True)
    
    lmxe_dir = sq_dir / 'lmxe' / pdf_type / 'systemwise'
    lmxe_paths = lmxe_dir.glob(f'{sqid}*.lmxe')
    lmxe_paths = sorted(lmxe_paths)
    
    tgt_lmxe_dir = sq_dir / 'lmxe' / pdf_type / 'partwise' / 'unaligned'
    tgt_lmxe_dir.mkdir(parents=True, exist_ok=True)
    
    tgt_metadata_dir = sq_dir / 'metadata' / pdf_type / 'partwise' / 'unaligned'
    tgt_metadata_dir.mkdir(parents=True, exist_ok=True)
    
    for l_p in tqdm(lmxe_paths, leave=False):
      task_list.append((
        l_p,
        tgt_lmxe_dir,
        tgt_metadata_dir,
        verify,
      ))
  
  if enable_multi_process:
    results = run_parallel(
      _split_partwise_process, 
      task_list, 
      show_progress=True,
      progress_desc="Splitting lmxe (multi-process)"
    )
    
    for seg_id, err in results:
      if err is not None:
        with open(errout, 'a', encoding='utf-8') as f:
          print(err, file=f)
  
  else:
    pbar = tqdm(task_list, desc="Splitting lmxe")
    for l_p, tgt_lmxe_dir, tgt_metadata_dir, verify in pbar:
      pbar.set_description(f"Splitting lmxe {l_p.stem}")
      seg_id, err = _split_partwise_process(
        l_p,
        tgt_lmxe_dir,
        tgt_metadata_dir,
        verify,
      )
      
      if err is not None:
        with open(errout, 'a', encoding='utf-8') as f:
          print(err, file=f)
  
  time.sleep(2) # ensure all file operations are completed before verification


if __name__ == '__main__':
  parser = get_argument_parser()
  args = parser.parse_args()
  
  main(args)