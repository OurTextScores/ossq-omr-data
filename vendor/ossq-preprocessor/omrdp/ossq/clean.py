import argparse
from pathlib import Path
import shutil

from tqdm.auto import tqdm

from omrdp.utils import get_ts, get_argument_parser, load_ossq_metadata, load_ossq_score_list
from omrdp.utils.musescore import convert_mscx_to_musicxml



def main(args:argparse.Namespace):
  base_dir = Path(args.base_dir)
  paths = args.path
  tgt_score_list = args.list_path
  
  data_dir = base_dir / 'data'
  score_dir = base_dir / 'scores'
  
  if tgt_score_list:
    data = load_ossq_score_list(tgt_score_list)
  else:
    data = load_ossq_metadata(data_dir / 'scores.yaml')
  
  data = list(data.items())
  pbar = tqdm(data)

  for _, body in pbar:
    sqid = body['sqid']
    sq_dir = body['path']
    
    pbar.set_description(sq_dir)

    sq_dir = score_dir / sq_dir

    for path in paths:
      if '*' in path:
        target_paths = list(sq_dir.glob(path))
      else:
        target_paths = [ sq_dir / path ]
      
      for p in target_paths:
        print(f"Removing {p}")
        
        if p.is_dir():
          shutil.rmtree(p)
        elif p.is_file():
          p.unlink()



if __name__ == '__main__':
  parser = get_argument_parser()
  
  parser.add_argument(
    '--path',
    action='append'
  )
  
  args = parser.parse_args()
  

  main(args)