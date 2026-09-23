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
  print(f" Aligning parts in {pdf_type} PDFs...")
  print("---"*20)
  
  errout = base_dir / 'logs' / f'align_parts_abc_{pdf_type}_{get_ts()}.log'
  
  data_dir = base_dir / 'data'
  score_dir = base_dir / 'scores'
  
  if tgt_score_list:
    data = load_ossq_score_list(tgt_score_list)
  else:
    data = load_ossq_metadata(data_dir / 'scores.yaml')
  
  pbar = list(data.items())
  pbar = tqdm(pbar)
  
  old_seg_and_new_seg = []
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
    partwise_abc_dir = sq_dir / 'abc' / pdf_type / 'partwise' / 'unaligned'
    
    tgt_partwise_abc_dir = sq_dir / 'abc' / pdf_type / 'partwise'
    tgt_partwise_abc_dir.mkdir(parents=True, exist_ok=True)
    
    # load exceptions from yolo_infos.yaml, if exists
    exceptions = set()
    if isinstance(yolo_infos.staff_bbox['exceptions'], list):
      exceptions = set(yolo_infos.staff_bbox['exceptions'])
    
    ignores = set()
    if isinstance(yolo_infos.staff_bbox['ignores'], list):
      ignores = set(yolo_infos.staff_bbox['ignores'])
    
    system_ids = sq_dir.glob(f'./images/{pdf_type}/systemwise/{sqid}*.png')
    system_ids = [ 
      s.stem 
      for s in system_ids 
    ]
    system_ids = sorted(system_ids)
    
    for s_id in system_ids:
      if s_id in (exceptions | ignores):
        continue
      
      partwise_abc_files = partwise_abc_dir.glob(f'{s_id}*.abc')
      partwise_abc_files = sorted(partwise_abc_files)
      
      partwise_images = partwise_img_dir.glob(f'{s_id}*.png')
      partwise_images = [ 
        p 
        for p in partwise_images 
        if p.stem not in ignores
      ]
      partwise_images = sorted(partwise_images)
      
      if len(partwise_abc_files) != len(partwise_images):
        with open(errout, 'a') as f:
          print(f'{body["path"]} | {s_id} | {len(partwise_abc_files)}:{len(partwise_images)}', file=f)
      
      for i_p, a_p in zip(partwise_images, partwise_abc_files):
        if i_p.stem in exceptions:
          continue
        
        new_a_p = tgt_partwise_abc_dir / f'{i_p.stem}.abc'
        old_seg_and_new_seg.append((
          a_p.stem, 
          new_a_p.stem
        ))
        shutil.copy(
          a_p,
          new_a_p
        )
  
  with open(base_dir / f'partwise_abc_alignment_{pdf_type}.txt', 'w') as f:
    for old_seg, new_seg in old_seg_and_new_seg:
      print(f'{old_seg}, {new_seg}', file=f)


if __name__ == '__main__':
  parser = get_argument_parser()
  args = parser.parse_args()
  
  main(args)
