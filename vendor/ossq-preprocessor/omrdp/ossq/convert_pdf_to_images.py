import warnings
import argparse
from pathlib import Path

from tqdm import tqdm

from omrdp.utils import get_ts, get_argument_parser
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
from omrdp.utils.musescore import convert_pdf_to_images

# Suppress all warnings from music21
warnings.filterwarnings('ignore', module='music21.*')


def main(args:argparse.Namespace):
  base_dir = Path(args.base_dir)
  tgt_score_list = args.list_path
  pdf_type = args.pdf_type
  
  errout = base_dir / 'logs' / f'pdf_to_images_{pdf_type}_{get_ts()}.log'
  errout_f = open(errout, 'w', encoding='utf-8')
  data_dir = base_dir / 'data'
  score_dir = base_dir / 'scores'
  
  if tgt_score_list:
    data = load_ossq_score_list(tgt_score_list)
  else:
    data = load_ossq_metadata(data_dir / 'scores.yaml')
  
  print("---"*20)
  print(f"Converting {pdf_type} PDFs to images...")
  print("---"*20)
  
  data = list(data.items())
  pbar = tqdm(data)
  
  for score_id, body in pbar:
    sqid = body['sqid']
    sq_dir = body['path']
    
    pbar.set_description(sq_dir)
    
    sq_dir = score_dir / sq_dir
    pdf_path = sq_dir / f"{sqid}_{pdf_type}.pdf"
    
    if pdf_type == 'scanned' and not pdf_path.with_suffix('.csv').exists():
      continue
    
    if not pdf_path.exists():
      print(f"{sqid} : PDF not found", file=errout_f)
      continue
    
    out_dir = sq_dir / 'images' / pdf_type / 'original'
    out_dir.mkdir(parents=True, exist_ok=True)
    
    try:
      convert_pdf_to_images(pdf_path, out_dir)
    except Exception as e:
      print(f"{sqid} : Error converting PDF to images: {e}", file=errout_f)
  
  errout_f.close()


if __name__ == '__main__':
  parser = get_argument_parser()
  args = parser.parse_args()

  main(args)
