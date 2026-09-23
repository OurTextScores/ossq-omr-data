import argparse
from pathlib import Path

from tqdm import tqdm

from omrdp.utils import get_ts, get_argument_parser
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
from omrdp.utils.yolo import YOLOInfo, load_yolo_model, detect_staff_heights_by_batch


def main(args:argparse.Namespace):
  base_dir = Path(args.base_dir)
  tgt_score_list = args.list_path
  
  pdf_type = args.pdf_type
  
  reproduce = bool(args.reproduce)
  verify = bool(args.verify)
  
  print("---"*20)
  print(f" Detecting staff heights in {pdf_type} PDFs...")
  print("---"*20)
  
  yolo_model_name = args.yolo_model_name
  batch_size = args.batch_size
  device = args.device
  
  model = load_yolo_model(f'{yolo_model_name}.pt', Path.cwd() / 'checkpoints')
  
  errout = base_dir / 'logs' / f'yolo_detect_staff_heights_{pdf_type}_{get_ts()}.log'
  
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
    if not yolo_infos.system['merge_threshold']:
      with open(errout, 'a') as f:
        print(f'{sqid}: ls-system model infos not found in yolo_infos.yaml', file=f)
      continue
    
    if reproduce:
      if not yolo_infos.staff_height['model']:
        with open(errout, 'a') as f:
          print(f'{sqid}: staff height model infos not found in yolo_infos.yaml for reproduction', file=f)
        continue
      
      model = load_yolo_model(f"{yolo_infos.staff_height['model']}.pt", Path.cwd() / 'checkpoints')
    
    img_paths = sq_dir.glob(f'./images/{pdf_type}/cropped/{sqid}*.png')
    img_paths = sorted(img_paths)
    
    detect_staff_heights_by_batch(img_paths, model, batch_size, device=device)
    
    if not reproduce:
      yolo_infos.staff_height['model'] = yolo_model_name
      yolo_infos.write(yolo_infos_path)
    
    if verify:
      bbox_paths = (sq_dir / 'images' / pdf_type / 'cropped').glob(f'{sqid}*_staff_heights.txt')
      bbox_paths = sorted(bbox_paths)
      
      if len(bbox_paths) != len(img_paths):
        with open(errout, 'a') as f:
          for i_p in img_paths:
            b_p = i_p.with_name(i_p.stem + '_staff_heights.txt')
            if not b_p.exists():
              print(f'{i_p}', file=f)


if __name__ == '__main__':
  parser = get_argument_parser()
  
  parser.add_argument(
    '--reproduce',
    required=True,
    type=int,
    default=1,
  )
  
  parser.add_argument(
    '-n', '--batch-size',
    required=True,
    type=int,
    default=24,
  )
  
  parser.add_argument(
    '--device',
    required=True,
    type=str,
    default='cpu',
  )
  
  parser.add_argument(
    '--yolo-model-name',
    required=False,
    type=str,
    default='ls-yolo-staff-height-v2.0.0',
  )
  
  args = parser.parse_args()
  
  main(args)
