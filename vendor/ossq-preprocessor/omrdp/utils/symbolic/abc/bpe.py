"""
Build an ABC notation BPE vocabulary using HuggingFace tokenizers.
Adapted and modified from LEGATO's tokenizer.json file
https://huggingface.co/guangyangmusic/legato
"""

from pathlib import Path
from typing import Union

from tokenizers import Tokenizer
from tokenizers.models import BPE
from tokenizers.trainers import BpeTrainer
from tokenizers.pre_tokenizers import Sequence, Split
from tokenizers.decoders import BPEDecoder

UNK = "<|unknown|>"

PRE_TOKENIZER = Sequence([
  Split(
    pattern="\n", 
    behavior="isolated"
  ),
  Split(
    pattern=r'\||\[|\]|"|%|!|\$', 
    behavior="isolated"
  ),
  Split(
    pattern=r"\s", 
    behavior="merged_with_next"
  ),
])


def train_abc_tokenizer(
  abc_strings:list[str],
  vocab_size:int=4096,
  min_frequency:int=2,
  extra_special_tokens:list[str]=[],
  output_path:Union[str,Path,None]=None,
) -> Tokenizer:
  """
  Train a BPE tokenizer on a corpus of ABC notation strings.

  UNK is always id 0. extra_special_tokens are reserved after UNK in order
  (ids 1, 2, ...). You can also add them later via tokenizer.add_special_tokens().
  No post-processor, padding, or truncation is attached.
  """
  model = BPE(unk_token=UNK)
  tokenizer = Tokenizer(model)
  tokenizer.pre_tokenizer = PRE_TOKENIZER

  trainer = BpeTrainer(
    vocab_size=vocab_size,
    min_frequency=min_frequency,
    special_tokens=[UNK] + extra_special_tokens,
    end_of_word_suffix="</w>",
    show_progress=True,
  )

  tokenizer.train_from_iterator(
    abc_strings, 
    trainer=trainer
  )
  tokenizer.decoder = BPEDecoder(suffix="</w>")

  if output_path is not None:
    tokenizer.save(str(output_path))

  return tokenizer