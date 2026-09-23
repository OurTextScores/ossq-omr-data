import time
from pathlib import Path
import argparse

from operator import contains

import math
import random

import json
import csv

from tqdm import tqdm

import cv2
import numpy as np

import kernpy as kp

from omrdp.utils import get_argument_parser, get_ts
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
from omrdp.utils import run_parallel


def _split_partwise(
  k_p:Path,
  partwise_krn_dir:Path,
):
  krn_str = k_p.read_text(encoding='utf-8')
  krn_str = kp.get_kern_from_ekern(krn_str)
  
  try:
    document, _ = kp.loads(krn_str)
  except Exception as e:
    err = f"{k_p.stem:<20} {'None':>10}  {'None':>10}  {'FAILED':<16} {f'Parsing krn: {e}':<}"
    raise RuntimeError(err)
  
  spine_ids = document.get_spine_ids()
  part_numbers = list(reversed(range(1, len(spine_ids)+1)))
  
  for sid, pnum in zip(spine_ids, part_numbers):
    partwise_krn_path = partwise_krn_dir / f'{k_p.stem}:{pnum}.ekrn'
    lines = kp.dumps(
      document,
      encoding=kp.Encoding.eKern,
      spine_ids=[sid]
    ).split('\n')
    
    # replace part related lines
    # e.g. ['*part4', '*staff4', '*I"Part 4']
    # to ['*part1', '*staff1', '*I"Part 1']
    lines = lines[:1] + ['*part1', '*staff1', '*I"Part 1'] + lines[4:]
    
    partwise_krn_path.write_text(
      '\n'.join(lines), 
      encoding='utf-8'
    )


def _split_partwise_process(
  k_p:Path,
  partwise_krn_dir:Path,
):
  try:
    _split_partwise(k_p, partwise_krn_dir)
    return k_p.stem, None
  except Exception as e:
    return None, e


def main(args:argparse.Namespace):
  prj_root = Path(args.base_dir)
  verify = bool(args.verify)
  tgt_score_list = args.list_path
  
  pdf_type = args.pdf_type
  enable_multi_process = bool(args.multi_process)
  
  errout = prj_root / 'logs' / f'split_krn_partwise_{pdf_type}_{get_ts()}.log'
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
    
    krn_dir = sq_dir / 'krn' / pdf_type / 'systemwise'
    krn_paths = krn_dir.glob(f'{sqid}*.ekrn')
    krn_paths = sorted(krn_paths)
    
    partwise_krn_dir = sq_dir / 'krn' / pdf_type / 'partwise' / 'unaligned'
    partwise_krn_dir.mkdir(parents=True, exist_ok=True)
    
    for k_p in tqdm(krn_paths, leave=False):
      task_list.append((
        k_p,
        partwise_krn_dir
      ))
  
  if enable_multi_process:
    results = run_parallel(
      _split_partwise_process, 
      task_list, 
      show_progress=True,
      progress_desc=f"Splitting krn {pdf_type} (multi-process)"
    )
    for seg_id, err in results:
      if err is not None:
        with open(errout, 'a', encoding='utf-8') as f:
          print(err, file=f)
  else:
    pbar = tqdm(task_list, desc=f"Splitting krn {pdf_type}")
    for k_p, partwise_krn_dir in pbar:
      pbar.set_description(f"Splitting krn {pdf_type} {k_p.stem}")
      seg_id, err = _split_partwise_process(
        k_p,
        partwise_krn_dir
      )
      
      if err is not None:
        with open(errout, 'a', encoding='utf-8') as f:
          print(err, file=f)
  
  time.sleep(2) # ensure all file operations are completed before verification


if __name__ == '__main__':
  parser = get_argument_parser()
  args = parser.parse_args()

  main(args)