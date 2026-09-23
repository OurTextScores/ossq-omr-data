"""
Extended ABC (eABC) format
Utilities for tokenizing and parsing eABC

Parse plain ABC text into musical units and saves as eABC format
(analogous to eKern), with non-ASCII separators embedded in-place:
- SEP_A · (U+00B7 MIDDLE DOT): 
    boundary between any two adjacent tokens
- SEP_B § (U+00A7 SECTION SIGN): 
    boundary between pitch/rest and its duration

Tokenization is line-aware:

Header lines (line starts with [A-Za-z]:)
	- The field marker (e.g. "K:") is one token.
	- The remainder is split on spaces only 
  - each whitespace-separated word is kept intact, 
    so "Cmaj", "Bb", "bass" are never broken up by the musical regex.

Music lines (everything else)
	Tokens are matched by the musical regex (priority order):
	- Decoration: 
    `![^!]+!` 
    e.g. !fermata!, !p!
	- Double accidental: 
    `^^` or `__`
	- Single accidental: 
    `^`, `_`, or `=`
	- Pitch + octave: 
    `[A-Ga-g][',]*` 
    e.g. `A'`, `b,,,`, `C`
	- Rest / spacer: 
    `[zx]` 
    e.g. `z`, `x` (duration separate)
	- Duration: 
    `d+/d+` or `d+` or `/d+` or `/` 
    e.g. `3/2`, `2`, `/4`, `/`
	- Space: 
    (literal space) 
    beat-group boundary
	- Other:
    barlines, brackets, etc.

Remarks:
  Spaces and newlines are ISOLATED
  never merged with adjacent tokens.
"""

import re
from pathlib import Path

SEP_A = "·" 
SEP_B = "§" 

# Detects a header line
_HEADER_LINE_RE = re.compile(r"^[A-Za-z]:")

# Musical token regex — applied to non-header lines.
_MUSIC_PATTERN = re.compile(
  # decoration
  r"![^!]+!"
  # double-sharp and sharp
  r"|\^\^|\^" 
  # double-flat and flat
  r"|__|_"
  # natural sign
  r"|=" 
  # pitch + octave modifiers
  r"|[A-Ga-g][',]*" 
  # rests: (z) or (x)
  r"|[zx]" 
  # compound duration
  r"|\d+/\d+" 
  # integer duration
  r"|\d+" 
  # division duration
  r"|/\d+"
  # bare slash (half duration) 
  r"|/"
  # space (beam group boundary)
  r"| "
  # everything else: |, [, ], (, ), -, etc.
  r"|." 
)

_PITCH_RE    = re.compile(r"^[A-Ga-g][',]*$")
_REST_RE     = re.compile(r"^[zx]$")
_DURATION_RE = re.compile(r"^\d+/\d+$|^\d+$|^/\d+$|^/$")


# Internal helpers
def _is_whitespace(token:str) -> bool:
  return token in (" ", "\n")


def _tokenize_header_value(value:str) -> list[str]:
  """
  Split a header field value on spaces only, keeping spaces as tokens.
  e.g. "Cmaj" -> ["Cmaj"],  "1 bass" -> ["1", " ", "bass"]
  """
  tokens:list[str] = []
  word:list[str] = []
  
  for ch in value:
    if ch == " ":
      if word:
        tokens.append("".join(word))
        word = []
      tokens.append(" ")
    
    else:
      word.append(ch)
  
  if word:
    tokens.append("".join(word))
  
  return tokens


def _needs_sep_b(left:str, right:str) -> bool:
  """True when left is a pitch/rest and right is a duration."""
  return bool(
    (
      _PITCH_RE.match(left) or
      _REST_RE.match(left)
    ) and
    _DURATION_RE.match(right)
  )


def _last_real_token(parts: list[str]) -> str:
  """Return the last emitted token (not a separator, not whitespace)."""
  for part in reversed(parts):
    if part not in (SEP_A, SEP_B) and not _is_whitespace(part):
      return part
  return ""


# main abc->eabc tokenizer
def tokenize(text:str) -> list[str]:
  """
  Split ABC text into a flat list of musical tokens.
  - Header lines ([A-Za-z]: at start): field marker + whitespace-split value.
  - Comment lines (% at start): whitespace-split words (no musical regex).
  - Music lines (everything else): musical regex.
  - Newlines between lines are emitted as separate tokens.
  """
  lines = text.split("\n")
  
  tokens:list[str] = []
  for i, line in enumerate(lines):
    if i > 0:
      tokens.append("\n")
    
    if _HEADER_LINE_RE.match(line):
      tokens.append(line[:2]) # field marker, e.g. "K:"
      tokens.extend(_tokenize_header_value(line[2:])) # header values
    
    elif line.startswith("%"):
      # Comment / %% directive: keep as whitespace-split words
      tokens.extend(_tokenize_header_value(line))
    
    # music line: apply musical regex
    else:
      tokens.extend(_MUSIC_PATTERN.findall(line))
  
  return tokens


# converters
def abc_to_eabc(abc_str:str) -> str:
  """
  Insert SEP_A / SEP_B between tokens and return the eABC string.

  - Whitespace tokens (space, newline) are emitted as-is 
  - insert SEP_B between a pitch/rest and its duration,
  - otherwise insert SEP_A between consecutive non-whitespace tokens.
  """
  parts:list[str] = []
  
  tokens = tokenize(abc_str)
  prev_ws = True  # treat start-of-string as if after whitespace
  
  for tok in tokens:
    if _is_whitespace(tok):
      parts.append(tok)
      prev_ws = True
    
    else:
      if not prev_ws and parts:
        prev_tok = _last_real_token(parts)
        sep = SEP_B if _needs_sep_b(prev_tok, tok) else SEP_A
        parts.append(sep)
      
      parts.append(tok)
      prev_ws = False
  
  return "".join(parts)


def eabc_to_abc(eabc_str:str) -> str:
  return eabc_str.replace(SEP_A, "").replace(SEP_B, "")


def parse_eabc(
  abc_str:str, 
  abc_type:str,
) -> str:
  """
  abc_types:
    - abc: plain abc notation with no separators
    - eabc: split \s, \n, SEP_A. remove SEP_B
    - beabc: split \s, \n, SEP_A, SEP_B
    - cabc: character-level abc: split every character, including whitespace. no separators.
  """
  
  lines = abc_str.split('\n')
  lines = [
    l.strip()
    for l in lines
    if l.strip()
  ]
  abc_str = '\n'.join(lines)
  
  # replace whitespaces with tokens
  abc_str = abc_str.replace(' ', ' <s> ')
  abc_str = abc_str.replace('\n', ' <b> ')

  if abc_type == 'abc':
    abc_str = abc_str.replace(SEP_A, '').replace(SEP_B, '') # remove all separators
  elif abc_type == 'eabc':
    abc_str = abc_str.replace(SEP_A, ' ').replace(SEP_B, '') # use only SEP_A
  elif abc_type == 'beabc':
    abc_str = abc_str.replace(SEP_A, ' ').replace(SEP_B, ' ') # use all separators
  elif abc_type == 'cabc':
    abc_str = abc_str.replace(SEP_A, ' ').replace(SEP_B, ' ') # remove all separators
    abc_str = abc_str.split()
    tokens = []
    for t in abc_str:
      if t in ('<s>', '<b>'):
        tokens.append(t)
      else:
        tokens += list(t)
    abc_str = ' '.join(tokens)
  
  return abc_str.strip().split(" ")