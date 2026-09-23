import argparse
from dataclasses import asdict
from pathlib import Path

import cv2

from tqdm.auto import tqdm

from omrdp.utils import get_ts, get_argument_parser
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
from omrdp.utils.bbox import load_bboxs
from omrdp.utils.yolo import YOLOInfo


def main(args:argparse.Namespace):
  base_dir = Path(args.base_dir)
  tgt_score_list = args.list_path
  
  reproduce = bool(args.reproduce)
  verify = bool(args.verify)
  
  pdf_type = args.pdf_type
  
  print("---"*20)
  print(f" Cropping systems in {pdf_type} PDFs...")
  print("---"*20)
  
  errout = base_dir / 'logs' / f'yolo_crop_systems_{pdf_type}_{get_ts()}.log'
  
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
    
    alignment_path = sq_dir / f'{sqid}_{pdf_type}.csv'
    if pdf_type == 'scanned' and not alignment_path.exists():
      continue
    
    yolo_infos_path = sq_dir / 'images' / pdf_type / f'{sqid}_yolo_infos.yaml'
    if not yolo_infos_path.exists():
      with open(errout, 'a') as f:
        print(f'{sqid}: yolo_infos.yaml not found', file=f)
      continue
    
    yolo_infos = YOLOInfo.load(yolo_infos_path)
    
    if not yolo_infos.system['model']:
      with open(errout, 'a') as f:
        print(f'{sqid}: ls-system model name not found in yolo_infos.yaml', file=f)
      continue
    
    if reproduce and (
      yolo_infos.system['confidence_threshold'] == ''
      and yolo_infos.system['merge_threshold'] == ''
    ):
      with open(errout, 'a') as f:
        print(f'{sqid}: confidence_threshold and merge_threshold not found in yolo_infos.yaml', file=f)
      continue
    
    confidence_threshold = args.confidence_threshold
    merge_threshold = args.merge_threshold
    if reproduce:
      confidence_threshold = float(yolo_infos.system['confidence_threshold'])
      merge_threshold = float(yolo_infos.system['merge_threshold'])
    
    crop_image_dir = sq_dir / 'images' / pdf_type / 'cropped'
    crop_image_dir.mkdir(exist_ok=True, parents=False)
    
    yolo_bbox_paths = sq_dir.glob(f'./images/{pdf_type}/original/{sqid}*_yolo_bboxs.txt')
    yolo_bbox_paths = sorted(yolo_bbox_paths)
    
    for b_p in tqdm(yolo_bbox_paths, leave=False):
      # cropped system images will be saved as **/images/{pdf_type}/cropped/*.png
      image_path = b_p.name.replace('_yolo_bboxs.txt', '.png')
      image_path = b_p.with_name(image_path)
      image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
      
      crop_image_paths = []
      system_bboxs = []
      
      bboxs = load_bboxs(
        b_p,
        confidence_threshold=confidence_threshold,
        merge_threshold=merge_threshold,
      )

      for i, (lx, ly, rx, ry) in enumerate(bboxs):
        # save cropped iamge
        crop_image_path = crop_image_dir / f'{image_path.stem}:{str(i+1).zfill(4)}.png'
        crop_image = image[ly:ry, lx:rx]
        cv2.imwrite(crop_image_path, crop_image)
        
        crop_image_paths.append(crop_image_path)
        system_bboxs.append( (lx, ly, rx, ry) )
      
      system_bboxs_path = b_p.name.replace('_yolo_bboxs.txt', '_system_bboxs.txt')
      system_bboxs_path = b_p.with_name(system_bboxs_path)
      
      with open(system_bboxs_path, 'w') as f:
        for bbox in bboxs:
          f.write(f'{" ".join(map(str, bbox))}\n')
    
    yolo_infos.system['confidence_threshold'] = confidence_threshold
    yolo_infos.system['merge_threshold'] = merge_threshold
    
    if not reproduce:
      yolo_infos.write(yolo_infos_path)
    
    if not verify:
      continue
    
    lmxe_dir = sq_dir / 'lmxe' / 'unaligned'
    lmxe_paths = sorted(lmxe_dir.glob(f'{sqid}*.lmxe'))
    
    image_dir = sq_dir / 'images' / pdf_type / 'cropped'
    image_paths = sorted(image_dir.glob(f'{sqid}*.png')) 
    
    if len(lmxe_paths) != len(image_paths):
      with open(errout, 'a') as f:
        f.write(f'{sqid}: {len(lmxe_paths)} vs. {len(image_paths)}\n')


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
