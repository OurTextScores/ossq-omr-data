from pathlib import Path

from .bpe import UNK, PRE_TOKENIZER
from .bpe import train_abc_tokenizer
from .eabc import tokenize, abc_to_eabc, eabc_to_abc, parse_eabc


def merge_partwise_abcs(
  partwise_paths:list[Path|str],
  output_path:Path|str,
) -> Path:
  """Convert partwise ABC files into a single systemwise ABC file.

  Each partwise file has the structure:
  L:<unit>
  M:<meter>
  K:<key>
  V:1 <clef>
  V:1
    <notes line(s)>

  The systemwise output re-numbers voices (1..N) and adds a %%score header:
  %%score [ 1 2 ... N ]
  L:...
  M:...
  K:...
  V:1 <clef1>
  ...
  V:N <clefN>
  V:1
    <notes1>
  V:2
    <notes2>
  ...
  """
  partwise_paths = [
    Path(p) 
    for p in partwise_paths
  ]
  
  output_path = Path(output_path)
  
  if not output_path.suffix:
    output_path = output_path.with_suffix('.abc')

  header_lines = None  # get headers line (L:, M:, K:) from the first part
  voice_clefs = [] # clef strings e.g. ["treble", "treble", "alto", "bass"]
  voice_notes = [] # list of note line lists (notes can span multiple lines)

  for path in partwise_paths:
    content = path.read_text()
    lines = content.split('\n')
    # Drop trailing empty string produced by a final newline
    if lines and lines[-1] == '':
      lines = lines[:-1]
    
    part_headers = []
    part_clef = None
    notes_start = None

    for i, line in enumerate(lines):
      s = line.strip()
      if s.startswith(('L:', 'M:', 'K:')):
        part_headers.append(line)
      elif s.startswith('V:'):
        tokens = s[2:].split()  # tokens after "V:"
        if len(tokens) > 1:
          # Voice declaration with clef: "V:1 treble"
          part_clef = ' '.join(tokens[1:])
        else:
          # Voice notes marker: "V:1" — all remaining lines are notes
          notes_start = i + 1

    if header_lines is None:
      header_lines = part_headers

    voice_clefs.append(part_clef)
    voice_notes.append(
      lines[notes_start:] 
      if notes_start is not None 
      else []
    )

  n = len(partwise_paths)
  score_nums = ' '.join(
    str(i) 
    for i in range(1, n + 1)
  )

  output_lines = [f"%%score [ {score_nums} ]"]
  output_lines += header_lines
  
  for i, clef in enumerate(voice_clefs, start=1):
    output_lines.append(f"V:{i} {clef}")
  
  for i, notes_lines in enumerate(voice_notes, start=1):
    output_lines.append(f"V:{i}")
    output_lines += notes_lines

  output_path.write_text('\n'.join(output_lines) + '\n')

  return output_path


def inject_time_signatures(
  abc_str:str, 
  level:str,
  signatures:list[dict]
) -> str:
  if level not in {'systemwise', 'partwise'}:
    raise ValueError(f"Invalid level: {level}. Must be 'systemwise' or 'partwise'.")
  
  lines = abc_str.split('\n')
  
  unit_note_line_idx = None
  for idx, line in enumerate(lines):
    if line.strip().startswith('L:'):
      unit_note_line_idx = idx
      break
  
  if unit_note_line_idx is None:
    return abc_str
  
  # inject time signatures
  signature = signatures[0]
  numerator, denominator = signature['time']
  time_signature_line = f" M:{numerator}/{denominator}"
  
  out_lines = lines[:unit_note_line_idx+1] 
  out_lines += [time_signature_line]
  out_lines += lines[unit_note_line_idx+1:]
  
  return '\n'.join(out_lines).strip()