import time
import warnings
from pathlib import Path
import shutil
import argparse
from tqdm import tqdm

import musicdiff as md

from modules.lmxe.lmxe import linearize_lmxe, delinearize_lmxe
from modules.lmxe.lmxe.LMXEFile import LMXEFile, LMXEMetadata
from modules.lmxe.lmxe.symbolic.Pruner import Pruner
from modules.lmxe.lmxe.vocabulary import *
from modules.lmxe.lmxe.symbolic.MxlFile import MusicXMLFile
from modules.lmxe.lmxe.symbolic.part_to_score import parts_to_score 

from omrdp.utils import get_ts, get_argument_parser
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
from omrdp.utils import run_parallel
from omrdp.utils.symbolic.musicxml import SHORT, compare_scores

from omrdp.ossq.utils import split_musicxml_by_part

# Suppress all warnings from music21
warnings.filterwarnings('ignore', module='music21.*')


def _convert_lmxe_to_variant(
  l_p,
  variant,
  verify,
):
  lmxe = LMXEFile.load(l_p, include_metadata=True)
  
  if variant == 'rlmxe':
    vlmxe = lmxe.get_reduced()
  elif variant == 'plmxe':
    vlmxe = lmxe.get_part_by_part()
  
  vl_p = l_p.parent / f"{l_p.stem}.{variant}"
  vlmxe.write(vl_p, include_metadata=True)
  
  if verify:
    if variant == 'rlmxe':
      return
    
    lmxe_single_line = lmxe.to_single_line_str()
    vlmxe_reconv = vlmxe.get_lmxe()
    vlmxe_reconv_single_line = vlmxe_reconv.to_single_line_str()
    
    if lmxe_single_line != vlmxe_reconv_single_line:
      raise ValueError(f"{l_p.name}")


def _convert_lmxe_to_variant_process(l_p, variant, verify):
  try:
    _convert_lmxe_to_variant(l_p, variant, verify)
    return l_p.name, None
  except Exception as e:
    return l_p.name, e


def main(args:argparse.Namespace):
  prj_root = Path(args.base_dir)
  verify = bool(args.verify)
  tgt_score_list = args.list_path
  
  pdf_type = args.pdf_type
  level = args.level
  variant = args.lmxe_variant
  
  enable_multi_process = bool(args.multi_process)
  
  errout = prj_root / 'logs' / f'lmxe_to_variant_{pdf_type}_{level}_{variant}_{get_ts()}.log'
  
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
    
    temp_dir = sq_dir / 'temp'
    temp_dir.mkdir(exist_ok=True)
    
    lmxe_dir = sq_dir / 'lmxe' / pdf_type / level
    lmxe_paths = lmxe_dir.glob('*.lmxe')
    lmxe_paths = sorted(lmxe_paths)
    
    for l_p in lmxe_paths:
      task_list.append((
        l_p,
        variant,
        verify,
      ))
  
  if enable_multi_process:
    results = run_parallel(
      _convert_lmxe_to_variant_process, 
      task_list, 
      show_progress=True,
      progress_desc=f"Converting lmxe to {variant} {pdf_type} {level} (multi-process)"
    )
    for sqid, err in results:
      if err is not None:
        with open(errout, 'a', encoding='utf-8') as f:
          print(err, file=f)
  else:
    pbar = tqdm(task_list, desc=f"Converting lmxe to {variant} {pdf_type} {level}")
    for l_p, variant, verify in pbar:
      seg_id, err = _convert_lmxe_to_variant_process(
        l_p,
        variant,
        verify
      )
      if err is not None:
        with open(errout, 'a', encoding='utf-8') as f:
          print(err, file=f)



if __name__ == '__main__':
  parser = get_argument_parser()
  
  parser.add_argument(
    '--level', 
    type=str, 
    default='systemwise', 
    choices=['systemwise', 'partwise'], 
    required=True,
  )
  parser.add_argument(
    '--lmxe-variant',
    type=str,
    default='rlmxe',
    choices=['rlmxe', 'plmxe'],
  )
  
  args = parser.parse_args()
  
  main(args)