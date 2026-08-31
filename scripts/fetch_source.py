#!/usr/bin/env python3
"""Download, verify, and optionally safely extract a locked source archive."""
import argparse
import hashlib
import json
import os
import tarfile
import urllib.request
from pathlib import Path

CHUNK = 1024 * 1024


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def download(spec, destination, base_url=None):
    partial = destination.with_suffix(destination.suffix + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    url = (base_url.rstrip("/") + "/" + spec["filename"]) if base_url else spec["url"]
    request = urllib.request.Request(url, headers=headers)
    try:
        response = urllib.request.urlopen(request)
        if offset and response.status != 206:
            partial.unlink()
            offset = 0
            response.close()
            response = urllib.request.urlopen(url)
        with response, partial.open("ab" if offset else "wb") as out:
            while block := response.read(CHUNK):
                out.write(block)
    except Exception as exc:
        raise SystemExit(f"download failed; partial file is retained for retry: {exc}")
    partial.replace(destination)


def safe_extract(archive, destination):
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            target = (destination / member.name).resolve()
            if os.path.commonpath([root, target]) != str(root):
                raise SystemExit(f"unsafe archive member: {member.name}")
        tar.extractall(destination, filter="data")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="key from sources.lock.json")
    parser.add_argument("--lock", default="sources.lock.json", type=Path)
    parser.add_argument("--dest", default="sources", type=Path)
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--base-url", help="public archive base URL; overrides the lock URL")
    args = parser.parse_args()
    spec = json.loads(args.lock.read_text())["sources"].get(args.source)
    if not spec:
        raise SystemExit(f"unknown source: {args.source}")
    args.dest.mkdir(parents=True, exist_ok=True)
    archive = args.dest / spec["filename"]
    if not archive.exists() or archive.stat().st_size != spec["bytes"]:
        download(spec, archive, args.base_url)
    actual = digest(archive)
    if actual != spec["sha256"]:
        archive.unlink(missing_ok=True)
        raise SystemExit(f"SHA-256 mismatch for {archive}; removed corrupt file")
    print(f"verified {archive}")
    if args.extract:
        safe_extract(archive, args.dest)
        print(f"extracted {args.dest / spec['top_level']}")


if __name__ == "__main__":
    main()
