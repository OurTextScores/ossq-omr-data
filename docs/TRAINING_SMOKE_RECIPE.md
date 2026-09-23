# Real training smoke recipe

This is an integration test of the dataset builder and actual HOMR trainer, not a
benchmark. Two score-disjoint OSSQ synthetic scores are too small for performance claims.

Build one frozen `synthetic/train` score and one frozen `synthetic/valid` score with
`tools/build_ossq_stage2.py --score-list two-scores.txt --tracks synthetic`. The
successful 2026-08-31 run contained 552 train and 572 validation pairs. Load one index
item through `training.transformer.data_loader.DataLoader` before training.

From a HOMR checkout with its training environment activated:

```bash
export HOMR_RUN_SUFFIX=ossq_repro_smoke_s42
python -c '
from training.transformer.train import train_transformer
train_transformer(warm_start=True, dataset_index=["/path/train/index.txt"],
                  validation_index="/path/valid/index.txt", number_of_epochs=3,
                  number_of_files=552, seed=42,
                  checkpoint_folder="ossq_repro_smoke_s42")
'
```

The suffix prevents collision with a production model name derived from the same Git
commit. The explicit validation index is score-disjoint; do not use HOMR's default row
split here.

Acceptance record: loader image tensor `(1, 256, 1280)`, six 608-token branches; 3/3
epochs completed in 50.3 seconds; epoch-3 held-out `eval_accuracy=0.9766176566`; output
`pytorch_model_464-997b70a88c9f945b632f4129b036b2cd0972b2a3-ossq_repro_smoke_s42.pth`.
This only validates pipeline compatibility, not full-corpus quality.
