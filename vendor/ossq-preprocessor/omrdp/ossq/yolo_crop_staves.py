import math
import argparse
from pathlib import Path

import cv2
import strictyaml as syaml

from tqdm.auto import tqdm

from ultralytics import YOLO

from omrdp.utils import get_ts, get_argument_parser
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
from omrdp.utils.bbox import load_bboxs
from omrdp.utils.yolo import YOLOInfo, load_yolo_model, inference_by_batch



def main(args:argparse.Namespace):
  base_dir = Path(args.base_dir)
  tgt_score_list = args.list_path
  
  reproduce = bool(args.reproduce)
  
  pdf_type = args.pdf_type
  
  print("---"*20)
  print(f" Cropping staves in {pdf_type} PDFs...")
  print("---"*20)
  
  errout = base_dir / 'logs' / f'yolo_crop_staff_{pdf_type}_{get_ts()}.log'
  
  data_dir = base_dir / 'data'
  score_dir = base_dir / 'scores'
  
  if tgt_score_list:
    data = load_ossq_score_list(tgt_score_list)
  else:
    data = load_ossq_metadata(data_dir / 'scores.yaml')
  
  pbar = list(data.items())
  pbar = tqdm(pbar)
  
  for score_idx, (score_id, body) in enumerate(pbar):
    sqid = body['sqid']
    sq_dir = body['path']
    
    pbar.set_description(sq_dir)
    
    sq_dir = score_dir / sq_dir
    
    if pdf_type == 'scanned' and not (sq_dir / f'{sqid}_scanned.csv').exists():
      continue
    
    yolo_infos_path = sq_dir / 'images' / pdf_type / f'{sqid}_yolo_infos.yaml'
    if not yolo_infos_path.exists():
      with open(errout, 'a') as f:
        print(f'{sqid}: yolo_infos.yaml not found', file=f)
      continue
    
    yolo_infos = YOLOInfo.load(yolo_infos_path)
    if not yolo_infos.staff_bbox['model']:
      with open(errout, 'a') as f:
        print(f'{sqid}: ls-staff-bbox model name not found in yolo_infos.yaml', file=f)
      continue
    
    if reproduce and (
      yolo_infos.staff_bbox['confidence_threshold'] == ''
      and yolo_infos.staff_bbox['merge_threshold'] == ''
    ):
      with open(errout, 'a') as f:
        print(f'{sqid}: confidence_threshold and merge_threshold not found in yolo_infos.yaml', file=f)
      continue
    
    confidence_threshold = args.confidence_threshold
    merge_threshold = args.merge_threshold
    if reproduce:
      confidence_threshold = float(yolo_infos.staff_bbox['confidence_threshold'])
      merge_threshold = float(yolo_infos.staff_bbox['merge_threshold'])
    
    yolo_bbox_paths = sq_dir.glob(f'./images/{pdf_type}/systemwise/{sqid}*_yolo_bboxs.txt')
    yolo_bbox_paths = sorted(yolo_bbox_paths)
    
    for b_p in tqdm(yolo_bbox_paths, leave=False):
      image_path = b_p.name.replace('_yolo_bboxs.txt', '.png')
      image_path = b_p.with_name(image_path)
      image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
      
      crop_image_dir = sq_dir / 'images' / pdf_type / 'partwise'
      crop_image_dir.mkdir(exist_ok=True, parents=False)
      
      bboxs = load_bboxs(
        b_p, 
        confidence_threshold=confidence_threshold, 
        merge_threshold=merge_threshold,
        with_class=True,
      )

      for i, (cl, lx, ly, rx, ry) in enumerate(bboxs):
        crop_path = crop_image_dir / f'{image_path.stem}:{i+1}.png'
        crop = image[ly:ry, lx:rx]
        cv2.imwrite(crop_path, crop)
      
      if len(bboxs) != 4:
        with open(errout, 'a') as f:
          print(f'{body["path"]} | {b_p.stem.replace("_yolo_bboxs", "")} | {len(bboxs)}', file=f)
      
      elif len(bboxs) == 4 and [int(cl) for cl, *_ in bboxs] != [2, 2, 1, 0]:
        with open(errout, 'a') as f:
          print(f'{body["path"]} | {b_p.stem.replace("_yolo_bboxs", "")} | {[int(cl) for cl, *_ in bboxs]}', file=f)
    
    
    if not reproduce:
      yolo_infos.staff_bbox['confidence_threshold'] = confidence_threshold
      yolo_infos.staff_bbox['merge_threshold'] = merge_threshold
      
      yolo_infos.write(yolo_infos_path)



if __name__ == '__main__':
  parser = get_argument_parser()
  
  parser.add_argument(
    '--reproduce',
    required=True,
    type=int,
    default=1,
  )
  
  parser.add_argument(
    '--confidence-threshold',
    required=True,
    type=float,
    default=0.8,
  )
  
  parser.add_argument(
    '--merge-threshold',
    required=True,
    type=float,
    default=0.7,
  )
  
  args = parser.parse_args()
  
  main(args)