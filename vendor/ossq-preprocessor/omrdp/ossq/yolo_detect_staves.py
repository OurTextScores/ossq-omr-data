import argparse
from pathlib import Path

from tqdm.auto import tqdm

from omrdp.utils import get_ts, get_argument_parser
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
from omrdp.utils.yolo import YOLOInfo, load_yolo_model, inference_by_batch


def main(args:argparse.Namespace):
  base_dir = Path(args.base_dir)
  tgt_score_list = args.list_path
  
  reproduce = bool(args.reproduce)
  
  pdf_type = args.pdf_type
  
  print("---"*20)
  print(f" Detecting staves in {pdf_type} PDFs...")
  print("---"*20)
  
  yolo_model_name = args.yolo_model_name
  batch_size = args.batch_size
  device = args.device
  
  model = load_yolo_model(f'{yolo_model_name}.pt', Path.cwd() / 'checkpoints')
  
  errout = base_dir / 'logs' / f'yolo_detect_staff_{pdf_type}_{get_ts()}.log'
  
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
    if not yolo_infos.staff_height['target_height']:
      with open(errout, 'a') as f:
        print(f'{sqid}: ls-staff-height model infos not found in yolo_infos.yaml', file=f)
      continue
    
    if reproduce:
      if not yolo_infos.staff_bbox['model']:
        with open(errout, 'a') as f:
          print(f'{sqid}: staff bbox model infos not found in yolo_infos.yaml for reproduction', file=f)
        continue
      
      model = load_yolo_model(f"{yolo_infos.staff_bbox['model']}.pt", Path.cwd() / 'checkpoints')
    
    system_imgs = sq_dir.glob(f'./images/{pdf_type}/systemwise/{sqid}*.png')
    system_imgs = sorted(system_imgs)
    
    # batch inference
    results = inference_by_batch(system_imgs, model, batch_size, device=device)
    
    for res in tqdm(results, leave=False):
      img = res.orig_img
      names = res.names
      bboxs = res.boxes.xyxy
      cls = res.boxes.cls

      # skip if no bbox
      if len(bboxs) < 1:
        continue

      orig_path = Path(res.path)
      bboxs = bboxs.int().tolist()
      confs = res.boxes.conf.tolist()

      # merge coordinates and confidence values
      bboxs = [
        (cl, *coords, cf)
        for coords, cl, cf in zip(bboxs, cls, confs)
      ]
      
      # sort by y, x
      bboxs = sorted(bboxs, key=lambda x: (x[2], x[1]))

      # save bboxs
      o_path = orig_path.name.replace('.png', '_yolo_bboxs.txt')
      o_path = orig_path.with_name(o_path)
      
      with open(o_path, 'w') as f:
        for cl, lx, ly, rx, ry, cf in bboxs:
          f.write(f'{cl} {lx} {ly} {rx} {ry} {cf}\n')
    
    if not reproduce:
      yolo_infos.staff_bbox['model'] = yolo_model_name
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
    default='ls-yolo-staff-bbox-v1.0.1',
  )
  
  args = parser.parse_args()
  
  main(args)