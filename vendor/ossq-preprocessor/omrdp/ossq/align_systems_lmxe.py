import argparse
from pathlib import Path
import shutil

from tqdm import tqdm

from omrdp.utils import get_ts, get_argument_parser
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
from omrdp.utils.bbox import load_bboxs
from omrdp.utils.yolo import YOLOInfo, resize_systems


def main(args:argparse.Namespace):
  base_dir = Path(args.base_dir)
  tgt_score_list = args.list_path
  
  pdf_type = args.pdf_type
  
  print("---"*20)
  print(f" Aligning systems in {pdf_type} PDFs...")
  print("---"*20)
  
  errout = base_dir / 'logs' / f'align_systems_lmxe_{pdf_type}_{get_ts()}.log'
  
  data_dir = base_dir / 'data'
  score_dir = base_dir / 'scores'
  
  if tgt_score_list:
    data = load_ossq_score_list(tgt_score_list)
  else:
    data = load_ossq_metadata(data_dir / 'scores.yaml')
  
  pbar = list(data.items())
  pbar = tqdm(pbar)
  
  total_excluded_segments = []
  for score_idx, (score_id, body) in enumerate(pbar):
    sqid = body['sqid']
    sq_dir = body['path']
    
    pbar.set_description(sq_dir)
    
    sq_dir = score_dir / sq_dir
    
    # if the pdf type is 'scanned',
    # process only alignment exists
    if pdf_type == 'scanned' and not (sq_dir / f'{sqid}_scanned.csv').exists():
      continue
    
    yolo_infos_path = sq_dir / 'images' / pdf_type / f'{sqid}_yolo_infos.yaml'
    if not yolo_infos_path.exists():
      with open(errout, 'a') as f:
        print(f'{sqid}: yolo_infos.yaml not found', file=f)
      continue
      
    yolo_infos = YOLOInfo.load(yolo_infos_path)
    
    # load ignores and exceptions from yolo_infos.yaml, if exists
    ignores = set() # set of segment ids to skip e.g. excess bbox w/o contents
    if isinstance(yolo_infos.system['ignores'], list):
      ignores = set(yolo_infos.system['ignores'])
    
    exceptions = set() # set of segment ids to exclude from the dataset e.g. wrongly cropped systems
    if isinstance(yolo_infos.system['exceptions'], list):
      exceptions = set(yolo_infos.system['exceptions'])
    
    img_paths = sq_dir.glob(f'./images/{pdf_type}/systemwise/{sqid}*.png')
    img_paths = sorted(img_paths)
    img_paths = [
      p
      for p in img_paths
      if p.stem not in ignores
    ]
    
    lmxe_paths = sq_dir.glob(f'./lmxe/unaligned/{sqid}*.lmxe')
    lmxe_paths = sorted(lmxe_paths)
    
    musicxml_paths = sq_dir.glob(f'./musicxml/unaligned/{sqid}*.musicxml')
    musicxml_paths = sorted(musicxml_paths)
    
    metadata_paths = sq_dir.glob(f'./metadata/unaligned/{sqid}*.yaml')
    metadata_paths = sorted(metadata_paths)
    
    # if the number of lmxe files and image files do not match,
    # log the error and skip
    # this is just a sanity check,
    # ideally all problems should have been caught in the 'yolo_crop_systems' step.
    if len(lmxe_paths) != len(img_paths):
      with open(errout, 'a') as f:
        print(f'{sqid}: {len(lmxe_paths)} vs. {len(img_paths)}', file=f)
      continue
    
    tgt_lmxe_dir = sq_dir / 'lmxe' / pdf_type / 'systemwise'
    tgt_lmxe_dir.mkdir(parents=True, exist_ok=True)
    
    tgt_musicxml_dir = sq_dir / 'musicxml' / pdf_type / 'systemwise'
    tgt_musicxml_dir.mkdir(parents=True, exist_ok=True)
    
    tgt_metadata_dir = sq_dir / 'metadata' / pdf_type / 'systemwise'
    tgt_metadata_dir.mkdir(parents=True, exist_ok=True)
    
    paths = zip(img_paths, lmxe_paths, musicxml_paths, metadata_paths)
    
    for i_p, l_p, x_p, m_p in paths:
      seg_id = i_p.stem
      
      if seg_id in exceptions:
        total_excluded_segments.append(seg_id)
        continue
      
      new_l_p = tgt_lmxe_dir / f'{seg_id}.lmxe'
      shutil.copy(l_p, new_l_p)
      
      new_x_p = tgt_musicxml_dir / f'{seg_id}.musicxml'
      shutil.copy(x_p, new_x_p)
      
      new_m_p = tgt_metadata_dir / f'{seg_id}.yaml'
      shutil.copy(m_p, new_m_p)
  
  total_excluded_segments_path = base_dir / f'excluded_segments_{pdf_type}_lmxe_systemwise.txt'
  if total_excluded_segments_path.exists():
    shutil.copy(
      total_excluded_segments_path, 
      base_dir / f"{total_excluded_segments_path.stem}.txt.old"
    )
  
  with open(total_excluded_segments_path, 'w') as f:
    for seg_id in total_excluded_segments:
      print(seg_id, file=f)


if __name__ == '__main__':
  parser = get_argument_parser()
  args = parser.parse_args()
  
  main(args)
