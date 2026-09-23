from typing import Union
from operator import eq

from .vocabulary import PITCH_TOKENS
PITCH_TOKENS += ['rest']

def split_tokens_by_key_token(token_list, key_token, include_key=False, head=True, compare_fn=eq):
  groups = []
  
  cur_group = []
  
  for tok in token_list:
    if compare_fn(tok, key_token):
      if len(cur_group) > 0:
        groups.append(cur_group)
        cur_group = []
      
      if include_key:
        groups.append([tok])
      
      continue
    
    cur_group.append(tok)
  
  else:
    if head:
      groups.append(cur_group)
  
  return groups


def find_nth_token_index(tokens:list[str], n:int=2, token_set:Union[set|list]=PITCH_TOKENS) -> int:
  assert (n > 0 and n < len(tokens)+1) or (n < 0 and -n <= len(tokens)), f'n must be in the range of len(tokens)'

  seq = tokens
  c = 1
  if n < 0:
    seq = tokens[::-1]
    c = -1
  
  note_count = 0
  nth_token_index = -1

  for i, t in enumerate(seq):
    if t in token_set:
      note_count += 1
      
      if note_count == n*c:
        nth_token_index = i
        break
  
  if n < 0 and nth_token_index != -1:
    nth_token_index = len(seq) - nth_token_index - 1

  return nth_token_index