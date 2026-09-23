import subprocess
import time
import argparse
import shutil
from pathlib import Path

import strictyaml as syaml

from tqdm import tqdm

from bs4 import BeautifulSoup
import requests

from omrdp.utils import get_ts, get_argument_parser
from omrdp.utils import load_ossq_metadata, load_ossq_score_list
import omrdp.utils.const as const


def crawl_imslp(args):
  base_dir = Path(args.base_dir)
  tgt_score_list = args.list_path
  
  errout = base_dir / 'logs' / f'imslp_crawl_{get_ts()}.log'
  errout_f = open(errout, 'w', encoding='utf-8')
  
  data_dir = base_dir / Path('data')
  
  if tgt_score_list:
    tgt_score_list = load_ossq_score_list(tgt_score_list)
    tgt_score_list = set(tgt_score_list.keys())
  
  data_path = data_dir / 'scores_w_url.yaml'
  if not data_path.exists():
    shutil.copy(data_dir / 'scores.yaml', data_path)
  
  data = load_ossq_score_list()
  pbar = list(data.items())
  pbar = tqdm(pbar)
  
  cnt = 0
  
  for score_id, body in pbar:
    if tgt_score_list and score_id not in tgt_score_list:
      continue
    
    if body.get('imslp_url', None):
      continue
    
    start_time = time.time()
    
    sqid = body['sqid']
    imslp_id = body['imslp'][1:]
    
    try:
      res = requests.get(const.IMSLP_URL_FORMAT % { 'imslp_id': imslp_id })
    except:
      print(f'{sqid} : Failed to crawl', file=errout_f)
      continue
    
    if res.status_code != 200:
      print(f'{sqid} : Failed to crawl with status code {res.status_code}', file=errout_f)
      continue
    
    soup = BeautifulSoup(res.text, 'lxml')
    
    if 'Disclaimer' in soup.title.string:
      res = requests.get(const.IMSLP_DISCLAIMER_URL_FORMAT % { 'imslp_id': imslp_id })
      soup = BeautifulSoup(res.text, 'lxml')
    
    if '.pdf' in res.url:
      pdf_url = res.url
    else:
      pdf_url = soup.select_one('#sm_dl_wait').get('data-id')
    
    data[score_id]['imslp_url'] = pdf_url
    
    cnt += 1
    
    if cnt % 10 == 0:
      # save intermediate results every 10 crawls
      with open(data_path, 'w') as f:
        f.write(syaml.as_document(data).as_yaml())
      
      # change VPN country every 10 crawls to avoid download limits
      next_country = const.COUNTRIES[cnt // 10]
      pbar.set_description(f'{next_country}:{cnt}')
      subprocess.call([ 'nordvpn', 'c', next_country ])
    
    else:
      time.sleep( max( 30, 60 - ( time.time() - start_time ) ) )
  
  with open(data_dir / 'scores_w_url.yaml', 'w') as f:
    f.write(syaml.as_document(data).as_yaml())


def download_pdfs(args):  
  base_dir = Path(args.base_dir)
  tgt_score_list = args.list_path
  
  errout = base_dir / 'logs' / f'imslp_downlod_{get_ts()}.log'
  errout_f = open(errout, 'w', encoding='utf-8')
  
  data_dir = base_dir / Path('data')
  score_dir = base_dir / Path('scores')

  if tgt_score_list:
    tgt_score_list = load_ossq_score_list(tgt_score_list)
    tgt_score_list = set(tgt_score_list.keys())
  
  data = load_ossq_metadata(data_dir / 'scores.yaml')
  data = list(data.items())
  pbar = tqdm(data)
  
  cnt = 0
  
  for score_id, body in pbar:
    if tgt_score_list and score_id not in tgt_score_list:
      continue
    
    start_time = time.time()
    
    sqid = body['sqid']
    sq_dir = body['path']
    
    pbar.set_description(sq_dir)
    
    sq_dir = score_dir / sq_dir
    pdf_path = sq_dir / f'{sqid}_scanned.pdf'
    
    if pdf_path.exists():
      continue
    
    imslp_url = body['imslp_url']
    try:
      res = requests.get(imslp_url)
    except:
      print(f'{sqid} : Failed to download', file=errout_f)
      continue
    
    if res.status_code != 200:
      print(f'{sqid} : Failed to download with status code {res.status_code}', file=errout_f)
      continue
    
    with open(pdf_path, 'wb') as pdf_f:
      pdf_f.write(res.content)
    
    cnt += 1
    
    if cnt % 10 == 0:
      next_country = const.COUNTRIES[cnt // 10]
      pbar.set_description(f'{next_country}:{cnt}')
      subprocess.call([ 'nordvpn', 'c', next_country ])
    
    else:
      time.sleep( max( 30, 60 - ( time.time() - start_time ) ) )


def main(args:argparse.Namespace):
  is_crawl = bool(args.crawl)
  
  if is_crawl:
    crawl_imslp(args)
  else:
    download_pdfs(args)


if __name__ == '__main__':
  parser = get_argument_parser()
  
  # determine whether to crawl IMSLP or download pdf
  # 1: crawl IMSLP for pdf urls
  # 0: download pdfs using existing urls in metadata
  parser.add_argument(
    '-c', '--crawl',
    choices=[1, 0],
    default=1,
    type=int
  )
  args = parser.parse_args()
  
  main(args)