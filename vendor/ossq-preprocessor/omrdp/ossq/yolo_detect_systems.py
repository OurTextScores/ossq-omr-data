import argparse
from pathlib import Path
import shutil

from tqdm import tqdm

from omrdp.utils import get_ts, get_argument_parser
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
from omrdp.utils.yolo import YOLOInfo, load_yolo_model, detect_systems_by_batch


def main(args:argparse.Namespace):
  base_dir = Path(args.base_dir)
  tgt_score_list = args.list_path
  
  reproduce = bool(args.reproduce)
  
  pdf_type = args.pdf_type
  
  print("---"*20)
  print(f" Detecting systems in {pdf_type} PDFs...")
  print("---"*20)
  
  yolo_model_name = args.yolo_model_name
  batch_size = args.batch_size
  device = args.device
  
  model = load_yolo_model(f'{yolo_model_name}.pt', Path.cwd() / 'checkpoints')
  
  errout = base_dir / 'logs' / f'yolo_detect_systems_{pdf_type}_{get_ts()}.log'
  
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
    
    yolo_infos_path = sq_dir / 'images' / pdf_type / f'{sqid}_yolo_infos.yaml'
    
    if reproduce:
      if yolo_infos_path.exists():
        yolo_infos = YOLOInfo.load(yolo_infos_path)
        
        if not yolo_infos.system['model']:
          with open(errout, 'a') as f:
            print(f'{sqid}: system model infos not found in yolo_infos.yaml for reproduction', file=f)
          continue
        
        model = load_yolo_model(f"{yolo_infos.system['model']}.pt", Path.cwd() / 'checkpoints')
      
      else:
        with open(errout, 'a') as f:
          print(f'{sqid}: yolo_infos.yaml not found for reproduction', file=f)
        continue
    
    else:
      # reproduce = False
      # remove previous yolo_infos.yaml if exists.
      if yolo_infos_path.exists():
        shutil.copy(
          yolo_infos_path,
          sq_dir / 'images' / pdf_type / f'{sqid}_yolo_infos.yaml.backup'
        )
        yolo_infos_path.unlink()
    
    alignment_path = sq_dir / f'{sqid}_{pdf_type}.csv'
    if pdf_type == 'scanned' and not alignment_path.exists():
      continue
    
    page_imgs = sq_dir.glob(f'./images/{pdf_type}/original/{sqid}*.png')
    page_imgs = sorted(page_imgs)
    
    if pdf_type == 'scanned':
      
      page_range = alignment_path.read_text().splitlines()[0]
      if page_range == ':':
        page_imgs = page_imgs
      else:
        page_st, page_ed = page_range.split(':')
        
        if page_st == '':
          page_st = 1
        else:
          page_st = int(page_st)
        
        if page_ed == '':
          page_ed = None
        else:
          page_ed = int(page_ed)
        
        page_imgs = page_imgs[page_st-1:page_ed]
    
    # batch inference
    detect_systems_by_batch(page_imgs, model, batch_size, device=device)
    
    if not reproduce:
      yolo_infos = YOLOInfo(
        data_id=sqid,
        image_type=pdf_type
      )
        
      yolo_infos.system['model'] = yolo_model_name
      
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
    default='ls-yolo-system-v3.0.0',
  )
  
  args = parser.parse_args()
  
  main(args)