import copy
from pathlib import Path
from operator import contains
from collections import defaultdict
from dataclasses import dataclass, field

from xml.etree import ElementTree as ET

import strictyaml as syaml

from .vocabulary import *
from .utils import (
  split_tokens_by_key_token, 
  find_nth_token_index,
)

"""
Linearized MusicXML Extended (LMXE) file representations

Like original Linearized MusicXML (LMX), LMXE is a plain text file format
The base format '.lmxe' files represent single musical system.
The file starts with a header, which contains metadata about the LMXE file.

LMXE files have the following structure:
2. LMXE sequence
1. Metadata section

A LMXE sequence is a sequence of tokens representing a single musical system.
The sequence can contain multiple measures, each measure is represented by a separate line.
The sequence contains tokens from the vocabulary defined in `vocabulary.py`.
Tokens are separated by whitespace characters.

!! from LMXE v0.2.0, The Metadata section is optional !!
The metadata section follows YAML-like syntax and separated from the LMXE sequence by a triple-dashed line '---'.
The metadata section contains the following fields:
- version: LMXE file version
- score_type: type of the score
  - single: single staff score e.g. vionlin part score
  - multi: multi-part score e.g. string quartet score
  - grandstaff: score with grand staff e.g. piano score
  - mixed: mixed type score e.g. piano with violin part score
- dataset: name of the dataset (e.g. "open-score-string-quartets")
- score_id: ID of the score (if available)
- page_idx: index of the page in the score (if available)
- system_idx: index of the system in the page (if available)
- number_of_parts: number of parts in the score
- measure_start: starting measure number in the score (if available)
- measure_end: ending measure number in the score (if available)
- measure_numbers: list of measure numbers in the system (if available)
- signatures: list of time, key, and clef signatures for each measure and part (if available)
  - list of measures
    - list of parts
      - dictionary with keys: 'time', 'key', 'clef'
        - 'time': tuple of (beats, beat_type)
        - 'key': number of sharps/flats
        - 'clef': dict of clef types by clef name (e.g. {'1': 'G2', '2': 'F4'})
"""



# still in BETA, version may change in the future
LMXE_FILE_VERSION = "0.2.2"

def get_score_type(parts_dict:dict[str,list[ET.Element]]) -> str:
  keys = parts_dict.keys()

  if 'grandstaff' in keys and 'multi' in keys:
    return 'mixed'

  if 'grandstaff' in keys:
    return 'grandstaff'

  if 'multi' in keys:
    return 'multi'
  
  if 'multi' in keys and len(parts_dict['multi']) == 1:
    return 'single'
  
  raise ValueError("Cannot determine score type from parts_dict")


@dataclass
class LMXEMetadata:
  version:str = LMXE_FILE_VERSION
  score_type:str = ""
  reduced:bool = False
  dataset:str = ""
  score_id:str = ""
  page_idx:int = -1
  system_idx:int = -1 
  number_of_parts:int = 1
  measure_start:str = ''
  measure_end:str = ''
  measure_numbers:list[str]=field(default_factory=list)
  signature_injected:list[dict] = field(default_factory=list)
  signatures:list[list[dict]]=field(default_factory=list)
  # list of mesures, list of parts, { time:list[int,int], key:int, clef:dict[str,str] }
  number_of_measures:int = -1


  def __post_init__(self):
    self.page_idx = self._convert_to_int(self.page_idx)
    self.system_idx = self._convert_to_int(self.system_idx)
    self.number_of_parts = self._convert_to_int(self.number_of_parts)
    
    if self.signature_injected:
      self.signature_injected = [
        { k: self._convert_to_yes_no(v) for k, v in d.items() }
        for d in self.signature_injected
      ]

  
  def _convert_to_yes_no(self, value):
    if isinstance(value, bool):
      return value
    
    if isinstance(value, str):
      value = value.lower()
      if value in ['yes', 'true', '1']:
        return True
      elif value in ['no', 'false', '0']:
        return False
    
    raise ValueError(f"Cannot convert {value} to yes/no string")
  
  def _convert_to_int(self, value):
    if value and int(value) > -1:
      return int(value)
    
    return -1
  

  def __str__(self):
    # avoid empty lists in YAML output
    if not self.measure_numbers:
      self.measure_numbers = [ f'{i+1}' for i in range(self.number_of_measures) ]
    
    if not self.signature_injected:
      self.signature_injected = [ 
        { 'time': False, 'key': False, 'clef': False }
        for _ in range(self.number_of_parts)
      ]
    
    if not self.signatures:
      # default signatures
      self.signatures = [ 
        [ 
          {'time': [4, 4], 'key': 0, 'clef': {'1': 'G2'}} 
          for _ in range(self.number_of_parts) 
        ] 
        for _ in range(self.number_of_measures) 
      ]
    
    _str = []
    _str.append(f"version: {self.version}")
    _str.append(f"score_type: {self.score_type}")
    _str.append(f"reduced: {self.reduced}")
    _str.append(f"dataset: {self.dataset}")
    _str.append(f"score_id: {self.score_id}")
    _str.append(f"page_idx: {self.page_idx}")
    _str.append(f"system_idx: {self.system_idx}")
    _str.append(f"number_of_parts: {self.number_of_parts}")
    _str.append(f"measure_start: {self.measure_start}")
    _str.append(f"measure_end: {self.measure_end}")
    _str.append("measure_numbers: " + '\n' + syaml.as_document(self.measure_numbers).as_yaml().rstrip())
    _str.append("signature_injected: " + '\n' + syaml.as_document(self.signature_injected).as_yaml().rstrip())
    _str.append("signatures: " + '\n' + syaml.as_document(self.signatures).as_yaml().rstrip())
    return '\n'.join(_str)
  
  
  @staticmethod
  def get_empty() -> "LMXEMetadata":
    return LMXEMetadata(
      number_of_measures=1
    )
  
  
  @staticmethod
  def load(path:str|Path) -> "LMXEMetadata":
    if not isinstance(path, Path):
      path = Path(path)
    
    if path.suffix != '.yaml':
      raise ValueError(f"Expected .yaml file, got {path.suffix}")
    if not path.exists():
      raise ValueError(f"File not found: {path}")
    
    metadata:str = path.read_text(encoding='utf-8')
    metadata:dict = syaml.load(metadata).data
    
    return LMXEMetadata(**metadata)
  
  
  def write(self, path:str|Path):
    if not isinstance(path, Path):
      path = Path(path)
    
    if path.suffix != '.yaml':
      raise ValueError(f"Expected .yaml file, got {path.suffix}")
    
    path.write_text(str(self), encoding='utf-8')
  
  
  def copy(self) -> "LMXEMetadata":
    return copy.deepcopy(self)


SUFFIX_TO_VARIANT_NAME = {
  '.lmxe': 'lmxe',
  '.plmxe': 'plmxe',
  '.rlmxe': 'rlmxe',
}


"""Represents a Linearized MusicXML Extended file in memory"""
class LMXEFile:
  def __init__(
    self, 
    measures:list[str]|dict[str,list[str]]=None, 
    metadata:LMXEMetadata=None,
    variant:str='lmxe',
  ):
    self.measures = measures if measures else list()
    self.metadata:LMXEMetadata = metadata
    self.variant = variant
  
  
  @staticmethod
  def load(
    path:str|Path, 
    include_metadata:bool=False,
  ) -> "LMXEFile":
    """
    Loads a LMXE file from the given path.
    
    :param path: Path to the LMXE file
    :type path: str | Path
    :param include_metadata: Whether to parse metadata section
    :type include_metadata: bool
    :param variant: The variant of the LMXE file
    :type variant: str
    :return: Loaded LMXEFile instance
    :rtype: LMXEFile
    """
    if isinstance(path, str):
      path = Path(path)
      
    variant = SUFFIX_TO_VARIANT_NAME.get(path.suffix, 'lmxe')
    lmxe = LMXEFile(variant=variant)
    
    content = path.read_text(encoding='utf-8')
    lmxe._parse_text(
      content, 
      include_metadata=include_metadata,
    )
    
    return lmxe
  
  
  def _parse_text(self, content: str, include_metadata:bool=False):
    """
    splits the content into metadata and lmxe content.
    
    Args:
      content:str
        LMXE file content as a string
    
    Returns:
      None
    """

    splited = content.split('---\n')

    if len(splited) < 2:
      lmxe_str = splited[0]
      metadata_str = ''
    else:
      lmxe_str, metadata_str = splited
    
    lines = [
      line.strip() 
      for line in lmxe_str.split('\n') 
      if line.strip()
    ]
    
    if self.variant == 'plmxe':
      measures = {}
      cur_part = None
      for line in lines:
        if line.startswith('part:'):
          measures[line] = []
          cur_part = line
          continue
        
        if cur_part is None:
          continue
        
        if line.startswith('measure'):
          measures[cur_part].append(line)
      
    else:
      measures = lines
    
    self.measures = measures
    
    if include_metadata and metadata_str:
      metadata:dict = syaml.load(metadata_str.strip()).data
      self.metadata = LMXEMetadata(**metadata)
  
  
  def strip_stem_directions(self):
    """
    strip stem direction information from the measures
    which are not part of the original score but are injected during linearization
    this is to make the LMXE files more similar to the original MusicXML files
    """
    
    if self.variant == 'plmxe':
      stripped_measures = defaultdict(list)
      for part, measures in self.measures.items():
        for m in measures:
          tokens = m.split()
          stripped_measure = []
          for t in tokens:
            if t.startswith('stem:'):
              continue
            
            stripped_measure.append(t)
          
          stripped_measures[part].append(' '.join(stripped_measure))
      
      self.measures = dict(stripped_measures)
    
    else:
      stripped_measures = []
      for m in self.measures:
        tokens = m.split()
        stripped_measure = []
        for t in tokens:
          if t.startswith('stem:'):
            continue
          
          stripped_measure.append(t)
        
        stripped_measures.append(' '.join(stripped_measure))
      
      self.measures = stripped_measures
  
  
  def strip_injected_signatures(self):
    """
    strip injected signatures from the first measure of the system
    which are not part of the original score
    but are injected during linearization
    """
    
    assert self.variant != 'plmxe', "strip_injected_signatures is only applicable for non-part-by-part LMXE files"
    
    sig_inj = self.metadata.signature_injected
    
    tokens = self.measures[0].split()
    measure, tokens = [tokens[0]], tokens[1:]
    
    parts = split_tokens_by_key_token( tokens, 'part:', compare_fn=lambda x, y: y in x )
    
    for i, (p, pj) in enumerate(zip(parts, sig_inj)):
      new_part = [f'part:{i+1}']
      
      if all( not pj[sig] for sig in ['time', 'key', 'clef'] ):
        new_part += p
        measure += new_part
        continue
      
      # find first note in current measure
      first_note_index = find_nth_token_index(
        p, 
        1, 
        token_set=NOTE_PREFIX_TOKENS
      ) 
      attrs = p[:first_note_index]
      
      i = 0
      while i < len(attrs):
        t = attrs[i]
        
        if pj['time'] and t.startswith('time:'):
          i += 3
          continue
        
        if pj['key'] and t.startswith('key:'):
          i += 1
          continue
        
        if pj['clef'] and t.startswith('clef:'):
          i += 1
          if i < len(attrs) and attrs[i].startswith('staff:'):
            i += 1
          continue
        
        new_part.append(t)
        i += 1
      
      new_part += p[first_note_index:]
      measure += new_part
    
    self.measures[0] = ' '.join(measure)
  
  
  def strip_time_signatures(self) -> "LMXEFile":
    # get a copy of the LMXE file with only measure tokens, which is used for training the language model
    if self.variant == 'plmxe':
      reduced_measures = defaultdict(list)
      for part, measures in self.measures.items():
        for m in measures:
          tokens = m.split()
          reduced_measure = []
          for t in tokens:
            if t in (BEATS_TOKENS | BEAT_TYPE_TOKENS):
              continue
            
            reduced_measure.append(t)
          
          reduced_measures[part].append(' '.join(reduced_measure))
      
      self.measures = dict(reduced_measures)
    
    elif self.variant == 'lmxe':
      reduced_measures = []
      for m in self.measures:
        tokens = m.split()
        reduced_measure = []
        for t in tokens:
          if t in set(BEATS_TOKENS+BEAT_TYPE_TOKENS):
            continue
          
          reduced_measure.append(t)
        
        reduced_measure = ' '.join(reduced_measure)
        reduced_measures.append(reduced_measure)
      
      self.measures = reduced_measures
  
  
  def get_reduced(self) -> "LMXEFile":
    rlmxe = copy.deepcopy(self)
    
    if rlmxe.variant == 'rlmxe':
      return rlmxe
    
    rlmxe.strip_stem_directions()
    rlmxe.strip_time_signatures()
    
    rlmxe.variant = 'rlmxe'
    rlmxe.metadata.reduced = True
    
    return rlmxe
  
  
  def get_part_by_part(self) -> "LMXEFile":
    # get a copy of the LMXEFile follows partwise MusicXML structure
    plmxe = copy.deepcopy(self)
    
    if plmxe.variant == 'plmxe':
      return plmxe
    
    measures = defaultdict(list)
    for m in self.measures:
      measure_token, *tokens = m.split()
      tokens_by_part = split_tokens_by_key_token(tokens, key_token='part:', compare_fn=contains)
      for p_idx, part_tokens in enumerate(tokens_by_part):
        part_score_type_token, *part_tokens = part_tokens
        part_key = f"part:{p_idx+1} {part_score_type_token}"
        
        measures[part_key].append(' '.join([measure_token] + part_tokens))
    
    plmxe.measures = dict(measures)
    plmxe.variant = 'plmxe'
    
    return plmxe
  
  
  def get_lmxe(self) -> "LMXEFile":
    # convert partwise LMXE to regular LMXE format by merging the measures of each part
    lmxe = copy.deepcopy(self)
    
    if lmxe.variant in ['lmxe', 'rlmxe']:
      return lmxe
    
    measures = []
    
    part_measures = sorted(
      self.measures.items(), 
      key=lambda x: int(x[0].split()[0].split(':')[1]) # sort by part number
    )
    part_keys = [ part_key for part_key, _ in part_measures ]
    part_measures = [ part_measure for _, part_measure in part_measures ]
    for m_idx, measures_by_part in enumerate(zip(*part_measures)):
      lmxe_measure = ['measure']
      for p_idx, part_measure in enumerate(measures_by_part):
        part_key = part_keys[p_idx]
        measure_token, *tokens = part_measure.split()
        lmxe_measure += part_key.split()
        lmxe_measure += tokens
      
      measures.append(' '.join(lmxe_measure))
    
    lmxe.measures = measures
    lmxe.variant = 'lmxe'
    
    return lmxe
  
  
  def write(
    self, 
    path:str|Path, 
    include_metadata:bool=False,
  )->bool:
    """Writes LMXE sequence to a file"""
    
    if isinstance(path, str):
      path = Path(path)
    
    if self.variant == 'plmxe':
      measures = ''
      for key, part_measures in self.measures.items():
        measures += f"{key}\n"
        for m in part_measures:
          measures += f"\t{m}\n"
    
    elif self.variant in ['lmxe', 'rlmxe']:
      if isinstance(self.measures, list):
        measures = '\n'.join(self.measures)
      else:
        measures = self.measures
    
    with open(path, 'w') as f:
      f.write(measures + '\n')
      f.write('---\n')
      
      if include_metadata:
        assert self.metadata is not None, "Metadata is None, cannot write metadata section"
        assert isinstance(self.metadata, LMXEMetadata), "metadata must be an instance of LMXEMetadata"
        
        f.write(str(self.metadata))
    
    return True
  
  
  def __eq__(self, other):
    if not isinstance(other, LMXEFile):
      return False
    
    return self.measures == other.measures
  
  
  def to_single_line_str(self) -> str:
    if self.variant in ['lmxe', 'rlmxe']:
      measures = ' '.join(self.measures)
    
    elif self.variant == 'plmxe':
      measures = []
      for key, part_measures in self.measures.items():
        measures.append(key)
        for m in part_measures:
          measures.append(m)
      
      measures = ' '.join(measures)

    return measures.strip()
  
  
  @classmethod
  def from_single_line_str(
    cls, 
    lmxe_str:str,
    variant:str='lmxe'
  ) -> "LMXEFile":
    lmxe = lmxe_str.split()
    
    if variant in ['lmxe', 'rlmxe']:
      measures = split_tokens_by_key_token(lmxe, 'measure')
      measures = [ ' '.join(['measure'] + m) for m in measures ]
    
    elif variant == 'plmxe':
      measures = defaultdict(list)
      parts = split_tokens_by_key_token(lmxe, 'part:', compare_fn=contains)
      
      for p_idx, part_tokens in enumerate(parts):
        part_score_type_token, *part_tokens = part_tokens
        part_key = f"part:{p_idx+1} {part_score_type_token}"
        part_measures = split_tokens_by_key_token(part_tokens, 'measure')
        for m in part_measures:
          measures[part_key].append(' '.join(['measure'] + m))
    
    return cls(measures=measures, variant=variant)



def split_lmxe_partwise(
  lmxe=LMXEFile|Path|str,
  include_metadata:bool=False
)->list[LMXEFile]:
  if not isinstance(lmxe, LMXEFile):
    lmxe = LMXEFile.load(lmxe, include_metadata=include_metadata)
  
  metadata = lmxe.metadata
  number_of_parts = metadata.number_of_parts
  
  parts = [
    []
    for _ in range(number_of_parts)
  ]
  
  for m in lmxe.measures:
    measure_token, *tokens = m.split()
    tokens_by_part = split_tokens_by_key_token(tokens, key_token='part:', compare_fn=contains)
    
    for p_idx, part_tokens in enumerate(tokens_by_part):
      score_type_token, *part_tokens = part_tokens
      part_tokens = [ measure_token, f'part:1', 'single' ] + part_tokens
      part_tokens = ' '.join(part_tokens)
      parts[p_idx].append(part_tokens)
  
  partwise_lmxes = []
  
  for p_idx, part_measures in enumerate(parts):
    part_metadata = None
    if include_metadata:
      part_metadata = LMXEMetadata(
        score_type='single',
        dataset=metadata.dataset,
        score_id=metadata.score_id,
        page_idx=metadata.page_idx,
        system_idx=metadata.system_idx,
        number_of_parts=1,
        measure_start=metadata.measure_start,
        measure_end=metadata.measure_end,
        measure_numbers=metadata.measure_numbers,
        signature_injected=[
          metadata.signature_injected[p_idx]
        ],
        signatures=[
          [ m[p_idx ] ]
          for m in metadata.signatures
        ]
      )
    
    partwise_lmxes.append(
      LMXEFile(
        measures=part_measures,
        metadata=part_metadata
      )
    )
  
  return partwise_lmxes


def merge_partwise_lmxes(
  partwise_lmxes:list[LMXEFile|Path|str], 
  include_metadata:bool=False
)->LMXEFile:
  partwise_lmxes = [
    LMXEFile.load(p, include_metadata=include_metadata)
    if isinstance(p, (str, Path)) 
    else p
    for p in partwise_lmxes
  ]
  
  number_of_parts = len(partwise_lmxes)
  
  measures = []
  
  for measure_tokens in zip(*[ l.measures for l in partwise_lmxes ]):
    measure = ['measure']
    
    for p_idx, part_tokens in enumerate(measure_tokens):
      part_tokens = part_tokens.split()
      
      # remove 'measure', 'part:1', and 'single' tokens from the part tokens
      # use if statements to avoid failing when the tokens are not present
      if (
        len(part_tokens) > 0 
        and part_tokens[0] == 'measure'
      ):
        part_tokens = part_tokens[1:]
      
      if (
        len(part_tokens) > 0 
        and part_tokens[0].startswith('part:')
      ):
        part_tokens = part_tokens[1:]
      
      if (
        len(part_tokens) > 0 
        and part_tokens[0] == 'single'
      ):
        part_tokens = part_tokens[1:]
      
      part_tokens = [ f'part:{p_idx+1}', 'multi' ] + part_tokens
      measure += part_tokens
    
    measures.append(' '.join(measure))
  
  metadata = None
  # for score with multiple parts,
  # basic metadata fields will be propagated from the first part,
  # but signatures will be aggregated from all parts
  if include_metadata:
    # aggregate signatures from partwise_lmxes
    signatures = [ [] for _ in range(len(measures)) ]
    for l in partwise_lmxes:
      for i, s in enumerate(l.metadata.signatures):
        signatures[i].append(s[0])
    
    metadata = LMXEMetadata(
      score_type='multi',
      dataset=partwise_lmxes[0].metadata.dataset,
      score_id=partwise_lmxes[0].metadata.score_id,
      page_idx=partwise_lmxes[0].metadata.page_idx,
      system_idx=partwise_lmxes[0].metadata.system_idx,
      number_of_parts=number_of_parts,
      measure_start=partwise_lmxes[0].metadata.measure_start,
      measure_end=partwise_lmxes[0].metadata.measure_end,
      measure_numbers=partwise_lmxes[0].metadata.measure_numbers,
      signature_injected=[
        l.metadata.signature_injected[0]
        for l in partwise_lmxes
      ],
      signatures=signatures
    )
  
  return LMXEFile(
    measures=measures,
    metadata=metadata
  )