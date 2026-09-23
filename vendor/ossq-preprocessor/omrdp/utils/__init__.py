from datetime import datetime
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Union, Any, Optional, Callable, Iterable
from concurrent.futures import ProcessPoolExecutor, as_completed

import json
import strictyaml as syaml
from tqdm.auto import tqdm


get_ts = lambda: datetime.now().strftime('%Y-%m-%d-%H:%M:%S')
dformat = lambda d: json.dumps(d, indent=2)
dprint = lambda d: print(dformat(d))

PathLike = Union[Path, str]


def load_ossq_metadata(path:PathLike) -> dict[str,Any]:
  if isinstance(path, str):
    path = Path(path)
  
  assert path.exists(), "Metadata file not found"
  assert path.suffix in [ '.yaml', '.yml' ], "Only YAML file expected"

  with open(path, 'r') as f:
    data = syaml.load(f.read()).data
  
  metadata = {
    str(k): dict(
      sqid=f'sq{k}',
      xml_path=v['path']+f'/sq{k}.musicxml',
      **v
    )
    for k, v in data.items()
  }
  
  return metadata


def load_ossq_score_list(target_score_list_path:PathLike) -> dict[str,Any]:
  # target score list format:
  # .txt format containing path(s) to .mscx files
  # path should be relative to 'scores' directory
  target_score_list_path = Path(target_score_list_path)
  
  with open(target_score_list_path, 'r') as f:
    target_file_paths = [ Path(line.strip()) for line in f.readlines() ]
  
  metadata = {
    str(item.stem.replace('sq', '')): {
      'sqid': item.stem,
      'path': '/'.join(str(item.parent).split('/')[-2:])
    }
    for item in target_file_paths
  }
  
  return metadata


def get_argument_parser(args=None):
  parser = argparse.ArgumentParser()
  
  parser.add_argument(
    '-d', '--base_dir', 
    required=True, 
    type=str,
  )
  
  parser.add_argument(
    '-t', '--pdf-type',
    required=False,
    type=str,
    default='scanned',
    choices=['scanned', 'synthetic']
  )
  
  parser.add_argument(
    '-l', '--list-path', 
    required=False, 
    type=str,
    default='',
  )
  
  parser.add_argument(
    '-v', '--verify',
    required=False,
    choices=[1, 0],
    default=1,
    type=int
  )
  
  parser.add_argument(
    '-r', '--reduced',
    required=False,
    choices=[1, 0],
    default=0,
    type=int
  )
  
  parser.add_argument(
    '-m', '--multi-process',
    required=False,
    choices=[1, 0],
    default=0,
    type=int
  )
  
  return parser


def parse_log_file(
  log_file, 
  metadata, 
  dataset_score_dir, 
  include_pnum=False,
):
  include_pnum = int(include_pnum)
  exceptions = []
  
  with open(log_file, 'r') as f:
    lines = f.readlines()
  
  # skip header and separator lines
  lines = lines[2:]
  for line in lines:
    line = line.strip()
    if not line:
      continue
    
    parts = line.split()
    
    if len(parts) < (4+include_pnum):
      continue
    
    seg_id = parts[0]
    if include_pnum:
      seg_id = parts[0].replace('sq', '', 1)
      pnum = int(parts[1])
    else:
      pnum = 'N/A'
    
    raw_ned = parts[1+include_pnum]
    raw_ned = float(raw_ned) if raw_ned != 'None' else None
    real_ned = parts[2+include_pnum]
    real_ned = float(real_ned) if real_ned != 'None' else None
    verdict = str(parts[3+include_pnum])
    
    if verdict == "TRUE" and len(parts) > (4+include_pnum):
      verdict = 'tp'
      details = str(' '.join(parts[5+include_pnum:]))
      details = {
        el.split(': ')[0]: el.split(': ')[1]
        for el in details.split(', ')
        if ': ' in el
      }
    elif verdict == "false" and len(parts) > (4+include_pnum):
      verdict = 'fp'
      details_str = ' '.join(parts[5+include_pnum:]).replace('[fp only: ', '').replace(']', '')
      details = {
        kv.split(': ')[0]: kv.split(': ')[1]
        for kv in details_str.split(', ')
        if ': ' in kv
      }
    elif verdict == 'CONVERSION':
      verdict = 'tp'
      details = {
        'conversion error': '1'
      }
    else:
      verdict = parts[3+include_pnum].lower()
      details = ' '.join(parts[4+include_pnum:])
    
    if details is not None:
      if include_pnum:
        body = metadata[seg_id]
        sqid = body['sqid']
        path = body['path']

        src_musicxml = dataset_score_dir / path / 'temp' / f'{sqid}_P{pnum}_cleaned.musicxml'
        tgt_musicxml = dataset_score_dir / path/ 'temp' / f'{sqid}_P{pnum}_delin.musicxml'
      
        exceptions.append({
          'seg_id': sqid,
          'pnum': pnum,
          'raw_ned': raw_ned,
          'real_ned': real_ned,
          'verdict': verdict,
          'details': details,
          'src_musicxml': src_musicxml,
          'tgt_musicxml': tgt_musicxml,
        })
      else:
        exceptions.append({
          'seg_id': seg_id,
          'raw_ned': raw_ned,
          'real_ned': real_ned,
          'verdict': verdict,
          'details': details
        })
  
  return exceptions


def parse_log_and_get_exclusions(
  log_file_path:Path, 
  metadata, 
  dataset_score_dir, 
  fatal_error_set:set={
    'conversion error',
    'measure insert/delete', 
    'staff insert/delete',
    'staff group',
    'barline',
    'keysig', 'clef', 'tie',
    'note', 'note head', 'dot',
  },
  include_pnum=False,
):
  log = parse_log_file(
    log_file_path, 
    metadata, 
    dataset_score_dir,
    include_pnum=include_pnum
  )
  
  excluded_segments = list()
  known_errors = defaultdict(int)
  known_fatal_errors = defaultdict(int)
  
  error_cnt = 0
  failed_cnt = 0
  
  for entry in log:
    if entry['verdict'] == 'failed':
      excluded_segments.append(entry['seg_id'])
      failed_cnt += 1
      continue
  
    if entry['verdict'] == 'tp':
      for k, v in entry['details'].items():
        known_errors[k] += int(v)
      
      error_set = set(entry['details'].keys())
      is_fatal_errors = len(error_set & fatal_error_set) > 0
      if is_fatal_errors:
        
        for k, v in entry['details'].items():
          if k in fatal_error_set:
            known_fatal_errors[k] += int(v)
        
        excluded_segments.append(entry['seg_id'])
        error_cnt += 1
  
  return excluded_segments, len(log), known_errors, known_fatal_errors, error_cnt, failed_cnt


def print_exclusion_report (
  *,
  num_samples,
  excluded_segments:list,
  known_errors:dict,
  known_fatal_errors:dict,
  error_cnt:int,
  failed_cnt:int
):
  print("total:", num_samples)
  print("excluded segments:", len(excluded_segments))
  print("exclusion rate:", (len(excluded_segments) / num_samples) * 100)
  print()
  print("error segments:", error_cnt)
  print("failed segments:", failed_cnt)
  print()
  print("Known fatal errors:")
  print(json.dumps(dict(known_fatal_errors), indent=2))
  print()
  print("Known errors:")
  print(json.dumps(dict(known_errors), indent=2))


def run_parallel(
  fn:Callable, 
  args_list:list,
  show_progress:bool=False,
  progress_desc:str="Processing"
) -> Iterable:
  """Run fn(*args) for each args in args_list using ProcessPoolExecutor.
  Yields results in completion order."""
  with ProcessPoolExecutor(max_workers=12) as executor:
    futures = [executor.submit(fn, *args) for args in args_list]
    iter_ = as_completed(futures)
    
    if show_progress:
      iter_ = tqdm(iter_, total=len(futures), desc=progress_desc, dynamic_ncols=True)
    
    for future in iter_:
      yield future.result()