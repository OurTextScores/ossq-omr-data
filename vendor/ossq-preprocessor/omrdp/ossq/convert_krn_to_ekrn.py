import time
import warnings
import shutil
import subprocess
from pathlib import Path
import argparse

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
from omrdp.utils.symbolic.musicxml import SHORT, compare_scores

# Suppress all warnings from music21
warnings.filterwarnings('ignore', module='music21.*')


def _convert_krn_to_ekrn(
  temp_dir:Path,
  k_p:Path,
  verify:bool,
):
  if not k_p.exists():
    err = f"{k_p.stem:<20} {'None':>10}  {'None':>10}  {'FAILED':<16} {'krn file not found':<}"
    raise RuntimeError(err)
  
  try:
    doc, _ = kp.load(k_p)
  except Exception as e:
    err = f"{k_p.stem:<20} {'None':>10}  {'None':>10}  {'FAILED':<16} {f'Parsing krn: {e}':<}"
    raise RuntimeError(err)
  
  try:
    kp.dump(
      doc,
      k_p.with_suffix('.ekrn'),
      encoding=kp.Encoding.eKern
    )
  except Exception as e:
    err = f"{k_p.stem:<20} {'None':>10}  {'None':>10}  {'FAILED':<16} {f'Converting eKrn: {e}':<}"
    raise RuntimeError(err)
  
  if not verify:
    return
  
  try:
    reconv = k_p.with_suffix('.ekrn').read_text(encoding='utf-8')
    reconv = kp.get_kern_from_ekern(reconv)
  except Exception as e:
    err = f"{k_p.stem:<20} {'None':>10}  {'None':>10}  {'FAILED':<16} {f'Parsing eKrn: {e}':<}"
    raise RuntimeError(err)
  
  try:
    reconv_path = temp_dir / k_p.name
    with open(reconv_path, 'w', encoding='utf-8') as f:
      f.write(reconv)
  except Exception as e:
    err = f"{k_p.stem:<20} {'None':>10}  {'None':>10}  {'FAILED':<16} {f'Writing krn: {e}':<}"
    raise RuntimeError(err)


def _convert_krn_to_ekrn_process(*args):
  try:
    _convert_krn_to_ekrn(*args)
    return args[1].stem, None
  except Exception as e:
    return None, e



def main(args:argparse.Namespace):
  prj_root = Path(args.base_dir)
  verify = bool(args.verify)
  tgt_score_list = args.list_path
  
  pdf_type = args.pdf_type
  enable_multi_process = bool(args.multi_process)
  
  errout = prj_root / 'logs' / f'krn_to_ekrn_{pdf_type}_{get_ts()}.log'
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
    krn_paths = krn_dir.glob(f'{sqid}*.krn')
    krn_paths = [
      p
      for p in krn_paths
      if '_with_time' not in p.stem
    ]
    krn_paths = sorted(krn_paths)
    
    for k_p in tqdm(krn_paths, leave=False):
      task_list.append((
        temp_dir,
        k_p,
        verify,
      ))
  
  if enable_multi_process:
    results = run_parallel(
      _convert_krn_to_ekrn_process, 
      task_list, 
      show_progress=True,
      progress_desc="Converting krn to ekrn (multi-process)"
    )
    for seg_id, err in results:
      if err is not None:
        with open(errout, 'a', encoding='utf-8') as f:
          print(err, file=f)
  else:
    pbar = tqdm(task_list, desc="Converting krn to ekrn")
    for temp_dir, k_p, verify in pbar:
      pbar.set_description(f"Converting krn to ekrn {k_p.stem}")
      seg_id, err = _convert_krn_to_ekrn_process(
        temp_dir,
        k_p,
        verify
      )
      
      if err is not None:
        with open(errout, 'a', encoding='utf-8') as f:
          print(err, file=f)
  
  if not verify:
    return
  
  verify_task_list = [
    (k_p, temp_dir/k_p.name)
    for temp_dir, k_p, *_ in tqdm(task_list, desc="Preparing verification tasks")
  ]
  
  time.sleep(2) # ensure all file operations are completed before verification
  
  results = compare_scores(
    verify_task_list,
    remove_stem_direction=False,
    enable_multi_process=enable_multi_process,
    is_lmx=False,
  )
  
  with open(errout, 'a', encoding='utf-8') as f:
    for i, (k_p, reconv_path) in enumerate(verify_task_list):
      res, err = results[i]
      
      seg_id = k_p.stem
      
      if err is not None:
        print(
          f"{seg_id:<20} {'None':>10}  {'None':>10}  {'FAILED':<16} {f'{str(err)}':<}", 
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