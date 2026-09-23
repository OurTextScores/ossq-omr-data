import re


def parse_ekrn(
  krn_str:str, 
  krn_type:str, 
  remove_stem_directions:bool=False
) -> list[str]:
  lines = krn_str.split('\n')
  
  # change the spine type to **kern
  # filter comment lines
  # filter out blank line
  lines = [
    l.strip().replace('**ekern', '**kern')
    for l in lines
    if l[:1] != '!' and l.strip()
  ]
  
  # re-join lines as one string
  krn_str = '\n'.join(lines)
  
  # remove measure numbers
  # which are numeric values after '='
  krn_str = re.sub("(?<=\=)\d+", "", krn_str)

  # replace whitespaces with tokens
  krn_str = krn_str.replace(' ', ' <s> ')
  krn_str = krn_str.replace('\t', ' <t> ')
  krn_str = krn_str.replace('\n', ' <b> ')
  
  # remove stem direction indicators
  if remove_stem_directions:
    krn_str = krn_str.replace(' /', '')
    krn_str = krn_str.replace(' \\', '')
    krn_str = krn_str.replace('·/', '')
    krn_str = krn_str.replace('·\\', '')

  if krn_type == 'krn':
    krn_str = krn_str.replace('·', '').replace('@', '') # remove all separators
  elif krn_type == 'ekrn':
    krn_str = krn_str.replace('·', ' ').replace('@', '') # use only dot separators
  elif krn_type == 'bekrn':
    krn_str = krn_str.replace('·', ' ').replace('@', ' ') # use both dot and at separators

  return krn_str.strip().split(" ")


def ekrn_to_krn(krn_str:str) -> str:
  krn_str = krn_str.replace('**ekern', '**kern')
  krn_str = krn_str.replace('·', '').replace('@', '')
  return krn_str.strip()


def inject_time_signatures(
  krn_str:str, 
  level:str,
  signatures:list[dict]
) -> str:
  if level not in {'systemwise', 'partwise'}:
    raise ValueError(f"Unsupported level: {level}")
  
  lines = krn_str.split('\n')
  
  first_measure_line_idx = None
  for i, line in enumerate(lines):
    if line.startswith('='):
      first_measure_line_idx = i
      break
  
  if first_measure_line_idx is None:
    return krn_str
  
  if level == 'systemwise':
    time_signature_line = ""
    for sig in reversed(signatures):
      numerator, denominator = sig['time']
      time_signature_line += f"*M{numerator}/{denominator}\t"
  elif level == 'partwise':
    time_signature_line = ""
    signature = signatures[0]
    numerator, denominator = signature['time']
    time_signature_line += f"*M{numerator}/{denominator}\n"
  
  out_lines = lines[:first_measure_line_idx] 
  out_lines += [time_signature_line] 
  out_lines += lines[first_measure_line_idx:]
  
  return '\n'.join(out_lines).strip()