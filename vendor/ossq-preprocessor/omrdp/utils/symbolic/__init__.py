from pathlib import Path

from modules.lmxe.lmxe.LMXEFile import LMXEMetadata

from .krn import inject_time_signatures as inject_time_signatures_krn
from .abc import inject_time_signatures as inject_time_signatures_abc


def inject_time_signatures(
  symbolic_type:str,
  symbolic_str:str, 
  level:str,
  sym_metadata_path:str|Path,
) -> str:
  sym_metadata = LMXEMetadata.load(sym_metadata_path)
  sym_signatures = sym_metadata.signatures[0]
  
  if symbolic_type == 'krn':
    return inject_time_signatures_krn(symbolic_str, level, sym_signatures)
  elif symbolic_type == 'abc':
    return inject_time_signatures_abc(symbolic_str, level, sym_signatures)
  else:
    raise ValueError(f"Unsupported symbolic type: {symbolic_type}")


def remove_time_signatures(
  symbolic_type:str,
  symbolic_str:str
) -> str:
  assert symbolic_type in {'krn', 'abc'}, f"Unsupported symbolic type: {symbolic_type}"
  
  ts_line_prefixes = {
    'krn': '*M',
    'abc': 'M:'
  }
  
  lines = symbolic_str.split('\n')
  
  out_lines = [
    line 
    for line in lines 
    if not line.startswith(
      ts_line_prefixes[symbolic_type]
    )
  ]
  
  return '\n'.join(out_lines).strip()