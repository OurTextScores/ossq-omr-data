import argparse
from pathlib import Path
import shutil

from tqdm import tqdm

from omrdp.utils import get_ts, get_argument_parser
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
from omrdp.utils.yolo import YOLOInfo


def main(args:argparse.Namespace):
  base_dir = Path(args.base_dir)
  tgt_score_list = args.list_path
  
  pdf_type = args.pdf_type
  
  print("---"*20)
  print(f" Aligning systems in {pdf_type} PDFs...")
  print("---"*20)
  
  errout = base_dir / 'logs' / f'align_parts_lmxe_{pdf_type}_{get_ts()}.log'
  
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
    
    partwise_img_dir = sq_dir / 'images' / pdf_type / 'partwise'
    partwise_lmxe_dir = sq_dir / 'lmxe' / pdf_type / 'partwise' / 'unaligned'
    partwise_metadata_dir = sq_dir / 'metadata' / pdf_type / 'partwise' / 'unaligned'
    
    tgt_partwise_lmxe_dir = sq_dir / 'lmxe' / pdf_type / 'partwise'
    tgt_partwise_metadata_dir = sq_dir / 'metadata' / pdf_type / 'partwise'
    
    # load exceptions from yolo_infos.yaml, if exists
    ignores = set() # set of segment ids to skip e.g. excess bbox w/o contents
    if isinstance(yolo_infos.staff_bbox['ignores'], list):
      ignores = set(yolo_infos.staff_bbox['ignores'])
    
    exceptions = set() # set of segment ids to exclude from the dataset e.g. wrongly cropped staffs
    if isinstance(yolo_infos.staff_bbox['exceptions'], list):
      exceptions = set(yolo_infos.staff_bbox['exceptions'])
    
    system_ids = sq_dir.glob(f'./images/{pdf_type}/systemwise/{sqid}*.png')
    system_ids = [ 
      s.stem 
      for s in system_ids 
    ]
    system_ids = sorted(system_ids)
    
    for s_id in system_ids:
      if s_id in ignores:
        continue
      
      if s_id in exceptions:
        total_excluded_segments.append(s_id)
        continue
      
      partwise_lmxes = partwise_lmxe_dir.glob(f'{s_id}*.lmxe')
      partwise_lmxes = sorted(partwise_lmxes)
      
      partwise_metadata = [
        partwise_metadata_dir / f'{pw_l_p.stem}.yaml'
        for pw_l_p in partwise_lmxes
      ]
      
      partwise_images = partwise_img_dir.glob(f'{s_id}*.png')
      partwise_images = [ 
        p 
        for p in partwise_images 
        if p.stem not in ignores
      ]
      partwise_images = sorted(partwise_images)
      
      if len(partwise_lmxes) != len(partwise_images):
        with open(errout, 'a') as f:
          print(f'{body["path"]} | {s_id} | {len(partwise_lmxes)}:{len(partwise_images)}', file=f)
      
      for i_p, l_p, m_p in zip(partwise_images, partwise_lmxes, partwise_metadata):
        # remove partwise lmxe file for ignored staffs, 
        # simply remove the corresponding lmxe files without renaming
        if i_p.stem in exceptions:
          total_excluded_segments.append(i_p.stem)
          continue
        
        new_l_p = tgt_partwise_lmxe_dir / f'{i_p.stem}.lmxe'
        new_m_p = tgt_partwise_metadata_dir / f'{i_p.stem}.yaml'
        
        shutil.copy(
          l_p,
          new_l_p
        )
        shutil.copy(
          m_p,
          new_m_p
        )
  
  total_excluded_segments_path = base_dir / f'excluded_segments_{pdf_type}_lmxe_partwise.txt'
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
