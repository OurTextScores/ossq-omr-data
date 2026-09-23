import warnings
import copy
from pathlib import Path
import shutil

import xml.etree.ElementTree as ET

from tqdm.auto import tqdm

import music21
import musicdiff as md

from omrdp.utils import get_ts, get_argument_parser, load_ossq_metadata, parse_log_file
from omrdp.utils.symbolic.musicxml import annotate_musicxmls

warnings.filterwarnings('ignore', module='music21.*')


def main(args):
  prj_root = Path(args.base_dir)
  
  log_path = Path(args.log_path)
  if not log_path.exists():
    print(f"Log file not found: {log_path}")
    return
  
  data_dir = prj_root / 'data'
  score_dir = prj_root / 'scores'
  
  data = load_ossq_metadata(data_dir / 'scores.yaml')
  

  exceptions = parse_log_file(log_path, data, score_dir)
  print(f"Found {len(exceptions)} exceptions in log file.")
  
  annotated_musicxmls = annotate_musicxmls(exceptions, score_dir)
  print(f"Annotated MusicXML files generated for {len(annotated_musicxmls)} exceptions.")


if __name__ == '__main__':
  parser = get_argument_parser()
  
  parser.add_argument(
    '--log-path',
    type=str,
    required=True,
  )
  
  args = parser.parse_args()

  main(args)
