#!/usr/bin/env python3
"""Download and verify the derived PDMX corpus shards named in sources.lock.json.

Fetching the corpus is the normal path; rebuilding it from Zenodo is for auditing the
build or changing the filters. So this exists to make the normal path verified rather
than convenient: every shard is checked against the digest recorded in git, and a shard
that does not match is deleted rather than left on disk to be trained on.

Digests come from the lockfile, never from a checksum file hosted beside the data.
Anyone able to replace a shard on the origin can replace a SHA256SUMS next to it, so a
same-origin checksum proves the transfer worked, not that the bytes are the ones we
published.

--split valid fetches 142MB instead of 1.94GB, which is all that evaluating a released
checkpoint needs.
"""

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

CHUNK = 1024 * 1024


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, destination: Path) -> None:
    """Resume into a .part file, so an interrupted 280MB shard is not re-fetched."""
    partial = destination.with_suffix(destination.suffix + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "pdmx-omr-corpus-fetch/1.0"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    response = urllib.request.urlopen(urllib.request.Request(url, headers=headers))
    if offset and response.status != 206:
        # The origin ignored the range; start over rather than append to a partial file
        # and produce a shard that is the right length and wrong bytes.
        partial.unlink()
        offset = 0
    with response, partial.open("ab" if offset else "wb") as out:
        while block := response.read(CHUNK):
            out.write(block)
    partial.replace(destination)


def fetch(lock: Path, dest: Path, split: str | None, *, verify_only: bool) -> int:
    corpus = json.loads(lock.read_text())["corpus"]
    shards = [s for s in corpus["shards"] if split in (None, s["split"])]
    if not shards:
        raise SystemExit(f"no shards for split {split!r}")
    dest.mkdir(parents=True, exist_ok=True)

    failures = 0
    for shard in shards:
        path = dest / shard["name"]
        if path.exists() and path.stat().st_size == shard["bytes"]:
            pass
        elif verify_only:
            print(f"{shard['name']}: absent")
            failures += 1
            continue
        else:
            print(f"fetching {shard['name']} ({shard['bytes'] / 1e6:.0f} MB)", flush=True)
            download(shard["url"], path)

        actual = digest(path)
        if actual == shard["sha256"]:
            print(f"{shard['name']}: verified")
        else:
            print(f"{shard['name']}: DIGEST MISMATCH\n  expected {shard['sha256']}\n  got      {actual}")
            if not verify_only:
                path.unlink()
                print("  removed; re-run to retry")
            failures += 1
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lock", type=Path, default=Path("sources.lock.json"))
    parser.add_argument("--dest", type=Path, default=Path("corpus"))
    parser.add_argument("--split", choices=("train", "valid"), help="default: both")
    parser.add_argument("--verify-only", action="store_true", help="check what is on disk")
    args = parser.parse_args()

    failures = fetch(args.lock, args.dest, args.split, verify_only=args.verify_only)
    if failures:
        raise SystemExit(f"{failures} shard(s) failed")
    print("all shards verified against the digests pinned in git")


if __name__ == "__main__":
    main()
