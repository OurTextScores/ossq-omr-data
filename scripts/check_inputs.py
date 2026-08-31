"""Validate the exact source root extracted from the locked OSSQ archive."""
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--ossq", type=Path, required=True)
args = parser.parse_args()

required = {
    args.ossq: ("README.md", "LICENSE.txt"),
}
for root, paths in required.items():
    missing = [path for path in paths if not (root / path).exists()]
    if missing:
        raise SystemExit(f"{root}: missing {', '.join(missing)}")
print("Locked OSSQ source check passed. Review source licences before deriving or releasing data.")
