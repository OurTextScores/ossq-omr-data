import warnings
from pathlib import Path
import shutil

import xml.etree.ElementTree as ET

import music21
import musicdiff as md

from modules.lmxe.lmxe.symbolic.MxlFile import MusicXMLFile
from modules.lmxe.lmxe.symbolic.part_to_score import parts_to_score
from modules.lmxe.lmxe.symbolic.Pruner import Pruner



def split_musicxml_by_part(
  musicxml:MusicXMLFile,
  sqid:str,
  out_dir:Path,
  strip_xml:bool=False,
  measure_numbers:list[str]|None=None,
  suffix:str='',
  prune_part:bool=False,
) -> list[Path]:
  """
  Splits a MusicXML file into separate files for each part. 
  Returns a list of paths to the generated part MusicXML files.
  """
  if prune_part:
    general_pruner = Pruner( prune_prints=False )
  
  part_musicxml_paths = []
  for part in musicxml.tree.getroot().findall('part'):
    part_musicxml_path = out_dir / f'{sqid}_{part.get("id")}{suffix}.musicxml'
    
    if prune_part:
      general_pruner.process_part(part)
    
    part_musicxml = parts_to_score(
      [('multi', part)], 
      measure_numbers=measure_numbers
    )
    part_musicxml = MusicXMLFile(part_musicxml)
    
    if strip_xml:
      part_musicxml.strip_musicxml()
    
    part_musicxml.write(part_musicxml_path)
    part_musicxml_paths.append(part_musicxml_path)
  
  
  return part_musicxml_paths
