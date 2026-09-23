import subprocess
import os
import shlex
from pathlib import Path

import cv2

import xml.etree.ElementTree as ET
import pdfplumber

from modules.lmxe.lmxe import delinearize_lmxe
from modules.lmxe.lmxe.symbolic.MxlFile import MusicXMLFile

from . import PathLike
from .image import crop_white_space, make_background_white


def run_musescore_converter(
  src_path:Path,
  tgt_path:Path,
  style_path:Path|None, # can be None
  *args, # tuples of (<option>, <value>)
)->None:
  # MuseScore's AppImage needs an X server on headless Linux.  Keep ordinary
  # desktops unchanged while allowing a deterministic wrapper such as
  # ``OMR_MUSESCORE='xvfb-run -a mscore'`` in CI and container builds.
  cmd = shlex.split(os.environ.get('OMR_MUSESCORE', 'mscore'))

  if style_path:
    cmd += [
      "-S",
      str(style_path),
    ]
    
  if args:
    for option, value in args:
      if option[0] != '-':
        option = '-' + option
        
      cmd += [
        option,
        str(value),
      ]
  
  cmd += [
    "-o",
    str(tgt_path),
    str(src_path),
  ]
  
  cmd = [
    str(c) 
    for c in cmd 
    if c.strip()
  ]

  # handle errors in outer function
  ps = subprocess.run(
    cmd,
    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
  )
  
  if ps.returncode != 0:
    raise Exception(
      "Command {} failed with code {}. MuseScore " "error messages:\n {}"
      .format(cmd, ps.returncode, ps.stderr.decode("UTF-8"))
    )


def convert_mscx_to_musicxml(
  src_path:PathLike,
  tgt_path:PathLike=None,
  style_path=None,
)->PathLike:
  src_path = Path(src_path)
  
  if tgt_path is None:
    tgt_path = src_path.with_suffix('.musicxml')
  else:
    tgt_path = Path(tgt_path)
  
  run_musescore_converter(
    src_path,
    tgt_path,
    style_path
  )
  
  return tgt_path


def convert_musicxml_to_mscx(
  src:PathLike|MusicXMLFile,
  tgt_path:PathLike,
  style_path=None,
)->PathLike:
  tgt_path = Path(tgt_path)
  
  if isinstance(src, MusicXMLFile):
    src_path = tgt_path.with_suffix('.musicxml')
    src.write(src_path)
  else:
    src_path = Path(src)
  
  run_musescore_converter(
    src_path,
    tgt_path,
    style_path
  )
  
  return tgt_path


def convert_mscx_to_pdf(
  src_path:PathLike,
  tgt_path:PathLike,
  style_path:str=None,
  dpi:int=300,
)->PathLike:
  src_path = Path(src_path)
  tgt_path = Path(tgt_path)
  
  run_musescore_converter(
    src_path,
    tgt_path,
    style_path,
    ('-r', str(dpi))
  )
  
  return tgt_path


def convert_pdf_to_images(
  src_path:PathLike,
  out_dir:PathLike,
  dpi:int=300,
)->None:
  if not src_path.exists():
    print(f"PDF file does not exist:{str(src_path)}", file=None)
    return
  
  out_dir.mkdir(parents=True, exist_ok=True)
  
  pdf = pdfplumber.open(str(src_path))

  for page in pdf.pages:
    page_number = str(page.page_number).zfill(4)
    image = page.to_image(resolution=dpi)
    
    image_path = out_dir
    image_path /= f'{src_path.stem.split("_")[0]}:{page_number}.png'
    image.save(str(image_path))


def convert_linearized_musicxml_to_image(
  src_path:PathLike, # path to lmx or lmxe file
  tgt_path:PathLike, # path to output image file
  style_path:PathLike=None,
  dpi:int=300,
)->PathLike:
  src_path = Path(src_path)
  tgt_path = Path(tgt_path)
  
  musicxml_path = tgt_path.with_suffix('.musicxml')
  
  musicxml = delinearize_lmxe(src_path)
  musicxml.strip_musicxml()
  musicxml.write(musicxml_path)
  
  mscx_path = tgt_path.with_suffix('.mscx')
  
  run_musescore_converter(
    musicxml_path,
    mscx_path,
    style_path,
    ('--force', ''),
  )
  
  run_musescore_converter(
    mscx_path,
    tgt_path,
    None,
    ('-r', str(dpi)),
    ('--force', ''),
  )
  
  rendered_path = tgt_path.with_name(f'{tgt_path.stem}-2.png')
  
  img = cv2.imread(rendered_path, cv2.IMREAD_UNCHANGED)
  img = make_background_white(img)
  img = crop_white_space(img, ratio=0.001)
  cv2.imwrite(tgt_path, img)
  
  # clean up intermediate files
  for r_i_p in tgt_path.parent.glob(f'{tgt_path.stem}-*.png'):
    r_i_p.unlink()
  
  return tgt_path
