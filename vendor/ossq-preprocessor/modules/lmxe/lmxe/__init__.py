import io
import os
import sys
from typing import Union, Optional
from pathlib import Path
import xml.etree.ElementTree as ET

from .Linearizer import Linearizer, LMXELinearizer
from .Delinearizer import Delinearizer, LMXEDelinearizer
from .LMXEFile import LMXEFile, LMXEMetadata, get_score_type
from .symbolic.MxlFile import MxlFile, MusicXMLFile
from .symbolic.part_to_score import part_to_score, parts_to_score

PathLike = Union[str, Path]


def load_lmx(path:Union[str, Path]) -> str:
  """
  Load a LMX file from the given path.
  
  :param path: Path to the LMX file.
  :return: Content of the LMX file as a string.
  """
  if isinstance(path, str):
    path = Path(path)
  
  if not path.exists():
    raise FileNotFoundError(f"LMX file not found: {path}")
  
  with open(path, 'r', encoding='utf-8') as f:
    return f.readline()


def linearize_lmx(xml: str):
  xml_tree = ET.ElementTree(ET.fromstring(xml))
  mxl = MxlFile(xml_tree)
  
  try:
    part = mxl.get_piano_part()
  except:
    part = mxl.tree.find("part")
  
  if part is None or part.tag != "part":
    print("No <part> element found.", file=sys.stderr)
    exit()
  
  linearizer = Linearizer(errout=sys.stderr)
  linearizer.process_part(part)
  output_lmx = " ".join(linearizer.output_tokens)

  return output_lmx


def delinearize_lmx(input_lmx:str) -> str:
  delinearizer = Delinearizer( errout=sys.stderr )
  delinearizer.process_text( input_lmx )
  score_etree = part_to_score( delinearizer.part_element )
  
  output_xml = str(
    ET.tostring(
      score_etree.getroot(),
      encoding="utf-8",
      xml_declaration=True
    ), 
    "utf-8"
  )

  return output_xml


def linearize_lmxe(
  *,
  xml:Union[PathLike,MusicXMLFile], 
  quiet=False,
  fail_on_unknown_tokens=False,
) -> list[list[LMXEFile]]:
  """
  Linearizes a MusicXML file into LMXE format.
  :param xml: Path to the MusicXML file or a MusicXMLFile instance
  :param reduced: Whether to use reduced token set (default: False)
  :param error_out: Stream to write error messages to (default: sys.stderr)
  :param fail_on_unknown_tokens: Whether to raise an error on unknown tokens (default: False)
  
  :return: A list of pages, where each page is a list of LMXEFile instances representing systems.
  """

  if isinstance(xml, (str, Path)):
    xml = MusicXMLFile.load_musicxml(xml)
  
  errout = io.StringIO()
  if quiet: 
    errout = open(os.devnull, 'w')

  """
  parts: {
    'parts': [(part_idx, ET.Element), ...],
    'piano': [(part_idx, ET.Element), ...]
  }
  """
  parts:dict[str,list[tuple[int, ET.Element]]] = xml.get_parts()
  score_type:str = get_score_type(parts) # {'single', 'multi', 'grandstaff', 'mixed'}

  linearizer = LMXELinearizer(
    score_type=score_type,
    errout=errout,
    fail_on_unknown_tokens=fail_on_unknown_tokens
  )

  linearizer.process_parts(parts)
  # score: list of pages
  # page: list of systems
  # system: [ number_of_parts, measure_nos, signature, signatures_injected, lmx_systems]
  # number_of_parts: int
  # measure_nos: list[str]
  # signature_injected: {
  #   'time': bool,
  #   'key': bool,
  #   'clef': bool
  # }
  # signature: [{
  #   'time': list[tuple[int,int]],
  #   'key': list[int],
  #   'clef': list[dict[str,str]]
  # }] * num_parts
  # lmx_systems: list of LMX strings for each part in the system
  raw_score = linearizer.get_lmx_score()
  
  errout.close()
  
  score = []
  for p_idx, raw_page in enumerate(raw_score):
    page = []
    for s_idx, system_infos in enumerate(raw_page):
      number_of_parts, measure_nos, signature_injected, signatures, system = system_infos
      number_of_measures = len(system)

      metadata = LMXEMetadata(
        score_type=score_type,
        dataset='',
        score_id='',
        page_idx=p_idx + 1,
        system_idx=s_idx + 1,
        number_of_parts=number_of_parts,
        measure_start=measure_nos[0],
        measure_end=measure_nos[-1],
        number_of_measures=number_of_measures,
        measure_numbers=measure_nos,
        signature_injected=signature_injected,
        signatures=signatures,
      )
      
      lmxe_file = LMXEFile(
        measures=system,
        metadata=metadata
      )
    
      page.append(lmxe_file)
    score.append(page)

  return score


def delinearize_lmxe(
  lmxe:LMXEFile|Path|str, 
  score_type='multi',
  quiet=False,
  force_inject_time:bool=False,
) -> MusicXMLFile:
  if not isinstance(lmxe, LMXEFile):
    lmxe = LMXEFile.load(lmxe, include_metadata=force_inject_time)
  
  errout = io.StringIO()
  if quiet:
    errout = open(os.devnull, 'w')
  
  delinearizer = LMXEDelinearizer(
    score_type=score_type,
    force_inject_time=force_inject_time,
    errout=errout
  )
  xml_parts = delinearizer.process_text( lmxe )
  
  errout.close()
  
  score_etree = parts_to_score(xml_parts)

  musicxml_file = MusicXMLFile(score_etree)

  return musicxml_file