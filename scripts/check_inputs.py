"""Refuse to build when an expected source checkout is absent or incomplete."""
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--ossq", type=Path, required=True)
parser.add_argument("--preprocessor", type=Path, required=True)
parser.add_argument("--homr", type=Path, required=True)
args = parser.parse_args()

required = {
    args.ossq: ("README.md",),
    args.preprocessor: ("README.md", "ossq_step_001.sh"),
    args.homr: ("training/omr_datasets/package_dataset.py",),
}
for root, paths in required.items():
    missing = [path for path in paths if not (root / path).exists()]
    if missing:
        raise SystemExit(f"{root}: missing {', '.join(missing)}")
print("Input check passed. Review source licences before running any download stage.")
