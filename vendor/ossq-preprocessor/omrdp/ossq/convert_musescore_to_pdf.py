import argparse
from pathlib import Path

from tqdm.auto import tqdm

from omrdp.utils import get_ts, get_argument_parser, load_ossq_metadata, load_ossq_score_list
from omrdp.utils.musescore import convert_mscx_to_pdf



def main(args:argparse.Namespace):
  prj_root = Path(args.base_dir)
  tgt_score_list = args.list_path
  
  errout = prj_root / 'logs' / f'musescore_to_pdf_{get_ts()}.log'
  
  data_dir = prj_root / 'data'
  score_dir = prj_root / 'scores'

  if tgt_score_list:
    data = load_ossq_score_list(tgt_score_list)
  else:
    data = load_ossq_metadata(data_dir / 'scores.yaml')
  
  print("---"*20)
  print(f"Converting musescore files to PDFs...")
  print("---"*20)
  
  data = list(data.items())
  pbar = tqdm(data)

  for score_idx, (score_id, body) in enumerate(pbar):
    sqid = body['sqid']
    sq_dir = body['path']
    
    pbar.set_description(sq_dir)

    sq_dir = score_dir / sq_dir

    mscx_path = sq_dir / f'{sqid}.mscx'
    pdf_path = sq_dir / f'{sqid}_synthetic.pdf'

    try:
      pdf_path = convert_mscx_to_pdf(
        mscx_path,
        pdf_path,
      )
    
    except Exception as e:
      with open(errout, 'a', encoding='utf-8') as errout_f:
        print(f"{sqid} : Failed Conversion: {e}", file=errout_f)
      continue




if __name__ == '__main__':
  parser = get_argument_parser()
  args = parser.parse_args()

  main(args)