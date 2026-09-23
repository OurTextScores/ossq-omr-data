import warnings
from pathlib import Path
import argparse

from strictyaml import exceptions
from tqdm import tqdm

import musicdiff as md
from musicdiff import DetailLevel

from modules.lmxe.lmxe.symbolic.MxlFile import MusicXMLFile
from modules.lmxe.lmxe.symbolic.part_to_score import parts_to_score 
from modules.lmxe.lmxe.symbolic.Pruner import Pruner

from omrdp.utils import get_ts, get_argument_parser
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
from omrdp.utils import run_parallel
from omrdp.ossq.utils import split_musicxml_by_part

# Suppress all warnings from music21
warnings.filterwarnings('ignore', module='music21.*')


def _clean_musicxml(
  xml_path:Path,
  temp_dir:Path,
  verify:bool,
):
  sqid = xml_path.stem
  xml = MusicXMLFile.load_musicxml(xml_path)
  
  xml.get_parts()
  # if there are more than 4 parts, keep only first 4 parts
  # known targets: sq7158117
  if len(xml.parts['multi']) > 4:
    root = xml.tree.getroot()
    parts = root.findall('part')
    for part in parts[4:]:
      root.remove(part)
  
  general_pruner = Pruner( prune_prints=False )
  barline_pruner = Pruner( 
    prune_barlines=True,
    prune_prints=False,
    prune_directions=False,
    prune_harmony=False,
    prune_slur_numbering=False,
  )
  
  # prune barlines first to avoid issues with dangling backup/forward sequences
  for part in xml.tree.getroot().findall('part'):
    barline_pruner.process_part(part)
  
  # remove dangling backup/forward sequences that may cause issues during ml/dl training
  xml.remove_dangling_invisible_elements()
  for part in xml.tree.getroot().findall('part'):
    general_pruner.process_part(part)
  
  # save cleaned MusicXML for full score
  xml.write(xml_path.with_name(f"{xml_path.stem}_cleaned.musicxml"))
  
  if not verify:
    return
  
  # save cleaned MusicXML parts
  cleaned_part_musicxml_paths = split_musicxml_by_part(
    musicxml=xml,
    sqid=sqid,
    out_dir=temp_dir,
    suffix='_cleaned',
  )
  
  # save uncleaned part MusicXML for comparison
  xml = MusicXMLFile.load_musicxml(xml_path)
  part_musicxml_paths = split_musicxml_by_part(
    musicxml=xml,
    sqid=sqid,
    out_dir=temp_dir,
    prune_part=True,
  )


def _clean_musicxml_process(*args):
  try:
    _clean_musicxml(*args)
    return args[0].stem, None
  except Exception as e:
    return None, e


def _verify_cleaned_musicxml_process(pred_path:Path, gt_path:Path):
  try:
    metrics = md._diff_omr_ned_metrics(
      predpath=pred_path,
      gtpath=gt_path,
      detail=DetailLevel.Default,
    )
    return gt_path.stem, metrics, None
  except Exception as e:
    return gt_path.stem, None, e


def main(args:argparse.Namespace):
  prj_root = Path(args.base_dir)
  verify = bool(args.verify)
  tgt_score_list = args.list_path
  
  enable_multi_process = bool(args.multi_process)

  errout = prj_root / 'logs' / f'clean_musicxml_{get_ts()}.log'
  
  data_dir = prj_root / 'data'
  score_dir = prj_root / 'scores'

  if tgt_score_list:
    data = load_ossq_score_list(tgt_score_list)
  else:
    data = load_ossq_metadata(data_dir / 'scores.yaml')
  
  data = list(data.items())
  pbar = tqdm(data, desc="Preparing MusicXML files")
  
  task_list = []
  for score_id, body in pbar:
    sqid = body['sqid']
    sq_dir = score_dir / body['path']
    
    temp_dir = sq_dir / 'temp'
    temp_dir.mkdir(exist_ok=True)
    
    xml_path = sq_dir / f'{sqid}.musicxml'
    
    task_list.append((
      xml_path,
      temp_dir,
      verify, 
    ))
  
  if enable_multi_process:
    results = run_parallel(
      _clean_musicxml_process,
      task_list,
      show_progress=True,
      progress_desc="Cleaning MusicXML files (multi-process)"
    )
  else:
    results = []
    for args in tqdm(task_list, desc="Cleaning MusicXML files"):
      sqid, err = _clean_musicxml_process(*args)
      results.append((sqid, err))
  
  for sqid, err in results:
    if err is not None:
      with open(errout, 'a', encoding='utf-8') as f:
        print(
          f"{str(sqid):<20} {'N/A'} {'None':>10}  {'None':>10}  {'CLEANING':<16} {str(err):<}", 
          file=f
        )
  
  if not verify:
    return
  
  verify_task_list = []
  for xml_path, temp_dir, _ in tqdm(task_list, desc="Preparing verification tasks"):
    sqid = xml_path.stem
    pred_paths = sorted(temp_dir.glob(f"{sqid}_P*_cleaned.musicxml"))
    for p_p in pred_paths:
      g_p = temp_dir / p_p.name.replace('_cleaned', '')
      verify_task_list.append((
        p_p,
        g_p,
      ))
  
  if enable_multi_process:
    results = run_parallel(
      _verify_cleaned_musicxml_process,
      verify_task_list,
      show_progress=True,
      progress_desc="Verifying cleaned MusicXML files (multi-process)"
    )
  else:
    results = []
    for predpath, gtpath in tqdm(verify_task_list, desc="Verifying cleaned MusicXML files"):
      sq_part_fn, metrics, err = _verify_cleaned_musicxml_process(predpath, gtpath)
      results.append((sq_part_fn, metrics, err))
  
  
  with open(errout, 'a', encoding='utf-8') as f:
    for sq_part_fn, metrics, err in results:
      if err is not None:
        print(f"{sq_part_fn:<20} {'ERR':>10} {str(err):<}", file=f)
        continue
      
      if metrics is None:
        print(f"{sq_part_fn:<20} {'FAILED':>10} None", file=f)
        continue
      
      print(f"{sq_part_fn:<20} {'SUCCESS':>10} {metrics.omr_ned}", file=f)


if __name__ == '__main__':
  parser = get_argument_parser()
  args = parser.parse_args()

  main(args)
