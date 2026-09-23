import argparse
from pathlib import Path

from tqdm.auto import tqdm

from omrdp.utils import get_ts, get_argument_parser
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
from omrdp.utils import run_parallel
from omrdp.utils.musescore import convert_mscx_to_musicxml


def _musescore_to_musicxml_process(*args):
  try:
    out_path = convert_mscx_to_musicxml(*args)
    return args[0].stem, out_path, None
  except Exception as e:
    return args[0].stem, None, e



def main(args:argparse.Namespace):
  prj_root = Path(args.base_dir)
  tgt_score_list = args.list_path
  
  enable_multi_process = bool(args.multi_process)
  
  errout = prj_root / 'logs' / f'musescore_to_musicxml_{get_ts()}.log'
  
  data_dir = prj_root / 'data'
  score_dir = prj_root / 'scores'

  if tgt_score_list:
    data = load_ossq_score_list(tgt_score_list)
  else:
    data = load_ossq_metadata(data_dir / 'scores.yaml')
  
  data = list(data.items())
  pbar = tqdm(data, desc="Preparing Tasks")
  
  task_list = []
  for score_id, body in pbar:
    sqid = body['sqid']
    sq_dir = score_dir / body['path']
    
    mscx_path = sq_dir / f'{sqid}.mscx'
    
    task_list.append((mscx_path,))
  
  if enable_multi_process:
    results = run_parallel(
      _musescore_to_musicxml_process,
      task_list,
      show_progress=True,
      progress_desc="Converting MuseScore files to MusicXML (multi-process)"
    )
  else:
    results = []
    for mscx_path in tqdm(task_list, desc="Converting MuseScore files to MusicXML"):
      sqid, out_path, err = _musescore_to_musicxml_process(mscx_path)
      results.append((sqid, out_path, err))
  
  with open(errout, 'a', encoding='utf-8') as f:
    for sqid, out_path, err in results:
      if err is not None:
        print(f"{sqid} : Failed Conversion: {str(err)}", file=f)


if __name__ == '__main__':
  parser = get_argument_parser()
  args = parser.parse_args()

  main(args)