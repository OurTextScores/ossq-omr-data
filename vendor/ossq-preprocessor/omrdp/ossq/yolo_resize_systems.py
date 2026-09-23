import argparse
from pathlib import Path

from tqdm import tqdm

from omrdp.utils import get_ts, get_argument_parser
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
from omrdp.utils.bbox import load_bboxs
from omrdp.utils.yolo import YOLOInfo, resize_systems


def main(args:argparse.Namespace):
  base_dir = Path(args.base_dir)
  tgt_score_list = args.list_path
  
  target_height = args.target_height
  reproduce = bool(args.reproduce)
  
  pdf_type = args.pdf_type
  
  print("---"*20)
  print(f" Resizing systems in {pdf_type} PDFs...")
  print("---"*20)
  
  errout = base_dir / 'logs' / f'yolo_resize_systems_{get_ts()}.log'
  
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
    if not yolo_infos.staff_height['model']:
      with open(errout, 'a') as f:
        print(f'{sqid}: ls-staff-height model name not found in yolo_infos.yaml', file=f)
      continue
    
    if reproduce and yolo_infos.staff_height['target_height'] == '':
      with open(errout, 'a') as f:
        print(f'{sqid}: target height is not found in yolo_infos.yaml', file=f)
      continue
    
    if reproduce:
      target_height = int(yolo_infos.staff_height['target_height'])
    
    img_paths = sq_dir.glob(f'./images/{pdf_type}/cropped/{sqid}*.png')
    img_paths = sorted(img_paths)
    
    staff_heights = []
    for i_p in tqdm(img_paths, desc='Calculating average staff height', leave=False):
      bbox_path = i_p.with_name(i_p.name.replace('.png', '_staff_heights.txt'))
      
      # pass image without staff height bbox
      if not bbox_path.exists():
        staff_heights.append(None)
        continue
      
      bboxs = load_bboxs(bbox_path, confidence_threshold=0.0)
      average_staff_height = sum([ y2 - y1 for (_, y1, _, y2) in bboxs ])
      average_staff_height /= len(bboxs)
      staff_heights.append(average_staff_height)
    
    if None in staff_heights:
      staff_heights_wo_none = [ n for n in staff_heights if n is not None ]
      score_average_staff_height = sum(staff_heights_wo_none) / len(staff_heights_wo_none)
      staff_heights = [ 
        n
        if n is not None
        else score_average_staff_height
        for n in staff_heights
      ]
    
    # resized system images will be saved as **/images/{pdf_type}/crop_resized/*.png
    resize_systems(
      img_paths, 
      staff_heights, 
      target_height=target_height,
      out_dirname='systemwise'
    )
    
    yolo_infos.staff_height['target_height'] = target_height
    
    if not reproduce:
      yolo_infos.write(yolo_infos_path)


if __name__ == '__main__':
  parser = get_argument_parser()
  
  parser.add_argument(
    '--target_height',
    required=True,
    type=int,
    default=18,
  )
  
  parser.add_argument(
    '--reproduce',
    required=True,
    type=int,
    default=1,
  )
  
  args = parser.parse_args()
  
  main(args)
