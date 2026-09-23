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


def _convert_musicxml_to_lmxe(
  score_info:dict, 
  score_dir:Path, 
  verify:bool,
  remove_stem_direction:bool,
):
  sqid = score_info['sqid']
  sq_dir = score_dir / score_info['path']
  
  xml_path = sq_dir / f'{sqid}_cleaned.musicxml'
  
  temp_dir = sq_dir / 'temp'
  temp_dir.mkdir(exist_ok=True)
  
  lmxe_dir = sq_dir / 'lmxe' / 'unaligned'
  lmxe_dir.mkdir(parents=True, exist_ok=True)
  
  musicxml_dir = sq_dir / 'musicxml' / 'unaligned'
  musicxml_dir.mkdir(parents=True, exist_ok=True)
  
  metadata_dir = sq_dir / 'metadata' / 'unaligned'
  metadata_dir.mkdir(parents=True, exist_ok=True)
  
  lmxe_score = linearize_lmxe(
    xml=xml_path,
    fail_on_unknown_tokens=False,
  )
  
  if verify:
    full_lmxe = LMXEFile()
    full_lmxe.metadata = lmxe_score[0][0].metadata.copy()
    full_lmxe.metadata.page_idx = -1
    full_lmxe.metadata.system_idx = -1
    full_lmxe.metadata.measure_numbers=[]
    full_lmxe.metadata.signatures=[]
  
  # save LMXE files per system
  for page in lmxe_score:
    for system in page:
      # system: LMXEFile
      system.metadata.dataset = 'open-score-string-quartets'
      system.metadata.score_id = sqid

      p_idx = system.metadata.page_idx # 1-based index
      s_idx = system.metadata.system_idx # 1-based index
      sample_id = f'{sqid}:{str(p_idx).zfill(4)}:{str(s_idx).zfill(4)}'
      
      lmxe_path = lmxe_dir / f'{sample_id}.lmxe'
      if remove_stem_direction:
        system.strip_stem_directions()
      system.write(lmxe_path, include_metadata=True)
      
      musicxml_path = musicxml_dir / f'{sample_id}.musicxml'
      system_musicxml = delinearize_lmxe(system, quiet=True)
      system_musicxml.write(musicxml_path)
      
      metadata_path = metadata_dir / f'{sample_id}.yaml'
      system.metadata.write(metadata_path)
      
      if verify:
        system.strip_injected_signatures()
        full_lmxe.measures += system.measures
        full_lmxe.metadata.measure_numbers += system.metadata.measure_numbers
        full_lmxe.metadata.signatures += system.metadata.signatures
  
  if verify:
    full_lmxe.metadata.measure_start = full_lmxe.metadata.measure_numbers[0]
    full_lmxe.metadata.measure_end = full_lmxe.metadata.measure_numbers[-1]
  
    full_lmxe_path = temp_dir / f'{sqid}.lmxe'
    full_lmxe.write(full_lmxe_path)
    
    delin_full_musicxml = delinearize_lmxe(full_lmxe_path)
    delin_part_musicxml_paths = split_musicxml_by_part(
      musicxml=delin_full_musicxml,
      sqid=sqid,
      out_dir=temp_dir,
      measure_numbers=full_lmxe.metadata.measure_numbers,
      strip_xml=True,
      suffix='_delin',
    )
  
    # save original MusicXML's parts for comparison
    musicxml = MusicXMLFile.load_musicxml(xml_path)
    part_musicxml_paths = split_musicxml_by_part(
      musicxml=musicxml,
      sqid=sqid,
      out_dir=temp_dir,
      strip_xml=True,
      suffix='_cleaned',
    )


def _convert_musicxml_to_lmxe_process(score_info, score_dir, verify, remove_stem_direction):
  try:
    _convert_musicxml_to_lmxe(score_info, score_dir, verify, remove_stem_direction)
    return score_info['sqid'], None
  except Exception as e:
    return score_info['sqid'], e


def main(args:argparse.Namespace):
  prj_root = Path(args.base_dir)
  verify = bool(args.verify)
  tgt_score_list = args.list_path
  
  enable_multi_process = bool(args.multi_process)
  remove_stem_direction = bool(args.remove_stem_direction)
  
  errout = prj_root / 'logs' / f'musicxml_to_lmxe_{get_ts()}.log'
  with open(errout, 'a', encoding='utf-8') as f:
    print(
      f"{'SQID':<12} {'P'} {'Raw NED':>10}  {'Real NED':>10}  {'Verdict':<16} Details", 
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

  if enable_multi_process:
    args_list = [
      (body, score_dir, verify, remove_stem_direction) 
      for _, body in data
    ]
    results = run_parallel(
      _convert_musicxml_to_lmxe_process, 
      args_list, 
      show_progress=True,
      progress_desc="Converting musicxml to lmxe (multi-process)"
    )
    for sqid, err in results:
      if err is not None:
        with open(errout, 'a', encoding='utf-8') as f:
          print(
            f"{sqid:<12} {'N/A'} {'None':>10}  {'None':>10}  {'CONVERSION':<16} {str(err):<}", 
            file=f
          )
  else:
    pbar = tqdm(data, desc="Converting musicxml to lmxe")
    for score_idx, (score_id, body) in enumerate(pbar):
      pbar.set_description(f"Converting musicxml to lmxe {body['path']}")
      _convert_musicxml_to_lmxe(
        body,
        score_dir,
        verify,
        remove_stem_direction,
      )
  
  if not verify:
    return
  
  # verification process
  # compare origianl musicxml with delinearized lmxe files
  # part-by-part
  task_list = []
  for score_idx, (score_id, body) in enumerate(tqdm(data, desc="Preparing verification tasks")):
    sqid = body['sqid']
    sq_dir = body['path']
    sq_dir = score_dir / body['path']
    
    temp_dir = sq_dir / 'temp'
    
    part_musicxml_paths = temp_dir.glob(f'{sqid}*_cleaned.musicxml')
    part_musicxml_paths = sorted(part_musicxml_paths)
    
    delin_part_musicxml_paths = temp_dir.glob(f'{sqid}*_delin.musicxml')
    delin_part_musicxml_paths = sorted(delin_part_musicxml_paths)
    
    task_list += list(zip(part_musicxml_paths, delin_part_musicxml_paths))
  
  time.sleep(2) # ensure all file operations are completed before verification
  
  results = compare_scores(
    task_list, 
    remove_stem_direction, 
    enable_multi_process,
    is_lmx=True,
  )
  
  with open(errout, 'a', encoding='utf-8') as f:
    for i, (cleaned_path, delin_path) in enumerate(task_list):
      res, err = results[i]
      
      sqid = cleaned_path.stem.split('_')[0]
      part_idx = i % 4 + 1
      
      if err is not None:
        print(f"{sqid:<12} {part_idx} {'None':>10}  {'None':>10}  {'FAILED':<16} {str(err):<}", file=f)
        continue
      
      if res is None:
        print(
          f"{sqid:<12} {part_idx} {'None':>10}  {'None':>10}  {'FAILED':<16} {'MusicDiff returned None':<}",
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
        f"{sqid:<12} {part_idx} {res['raw_ned']:>10.6f}  {res['real_ned']:>10.6f}  {verdict:<16} {detail}",
        file=f
      )



if __name__ == '__main__':
  parser = get_argument_parser()
  parser.add_argument(
    '--remove-stem-direction',
    type=int,
    default=0,
    help='Whether to remove stem direction information from the LMXE files.'
  )
  args = parser.parse_args()

  main(args)