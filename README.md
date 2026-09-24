# OSSQ-OMR data build

Code and provenance for reconstructing a portable HOMR Stage-2 OSSQ dataset from a
frozen OpenScore String Quartets source snapshot. This repository deliberately contains
**no scans, PDFs, MuseScore source files, trained weights, or generated crop payloads**;
the locked source archive is fetched separately and verified before extraction.

The resulting dataset is designed for a clean consumer: materialized images, relative
index paths, score-disjoint splits, notation sidecars, and a manifest digest. It is not
a replacement for the upstream OSSQ repository or its licence/provenance notices.

## Two artifacts, and which one you want

`sources.lock.json` locks two different things.

**`corpus` — the built staff-crop dataset.** `ossq-scanned-v2` has 39,137 windows
(35,226 train / 3,911 validation) from the scanned track, with v6 notation sidecars
and restored stem directions. This is what you train on:

```bash
make fetch-corpus                 # 888 MB, 39,137 windows
make fetch-corpus SPLIT=valid     #  85 MB,  3,911 windows - enough to evaluate a checkpoint
make verify-corpus                # re-check against the digests pinned in git
```

Shards are verified against digests held in this repository, not a checksum file sitting beside
the data on the origin. A shard whose digest does not match is deleted rather than left on disk
to be trained on. No score straddles a shard, and train and validation share none.

`ossq-scanned-v1` remains available at its original R2 prefix for consumers pinned to
the earlier lockfile. Its applicable stem directions are all `unknown`; use v2 for stem
training or evaluation. The v2 comparison found the same index rows, image bytes, and
token files, with zero changes to notation fields other than `stem`.

**`sources` — the locked OSSQ source snapshot.** For rebuilding the corpus with
`make build-stage2`, or auditing it.

The build is pinned in `corpus.build`: the homr commit it ran, torch, ultralytics and opencv
versions, the YOLO mode, and the SHA-256 of each of the three YOLO weight files. A rebuild that
does not reproduce this corpus can be diffed against those. The v2 `stem_rebuild` entry
pins the OSSQ and homr commits used for the stem repair; the detector crops and source
inputs were carried forward from v1.

**The synthetic track is not in this build.** OSSQ renders the same music from its MuseScore
sources, a larger set than the scanned track, and it has never been part of a training mixture.
Building it is another pass of `tools/build_ossq_stage2.py --tracks synthetic`.

## Locked source input

`sources.lock.json` is the authoritative record for the source artifact: its CDN URL,
byte length, SHA-256, archive layout, and publication date. `make extract-source`
downloads it with retry-safe partial-file retention, checks the exact SHA-256, and safely
extracts it under `sources/ossq-source/`. No Git checkout of an unrelated repository is
required to obtain the frozen input.

The lockfile uses the public R2 development origin. A future custom CDN domain can be
used without modifying the lockfile: `make extract-source ARCHIVE_BASE_URL=https://archives.example.org`.

## Build from scratch

```bash
git clone https://github.com/jhlusko/ossq-omr-data.git
cd ossq-omr-data

make extract-source
make check-inputs
```

## Build environment

The executable build needs a Linux environment with **Python 3.10--3.12**,
**MuseScore CLI** available as `mscore`, `xvfb-run` for headless Linux, and a CPU or
CUDA-capable PyTorch install.
Create an isolated environment and install the pinned build surface before running a
build:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements-build.txt
export PATH="$PWD/.venv/bin:$PATH"
mscore --version
```

The first crop run downloads the preprocessor's published YOLO weights. This is a
runtime model dependency, not hidden training input; the score/PDF source remains the
checksummed archive in `sources.lock.json`.

The source-to-crop/label pipeline is vendored and invoked by `make build-stage2`.
It emits one fail-closed HOMR dataset per track/split, with token and structured-notation
sidecars. See [the executable build notes](docs/BUILD_PIPELINE.md) for runtime
dependencies, source provenance, and a one-score smoke build.

The score-disjoint dataset-to-trainer acceptance recipe is in
[the training smoke recipe](docs/TRAINING_SMOKE_RECIPE.md).

## Release gates

- Preserve a per-work provenance table: source revision, scan URL, rights assertion,
  and every derived crop ID.
- Keep train/validation score-disjoint and test the assertion after packaging.
- Do not publish scans until their source rights are independently verified.
- Run a fresh-clone consumer test and `--verify-only` against the packaged tree before
  uploading it to a dataset host.

The expected host layout and card requirements should ship with every dataset release.

## License

MIT for this build documentation and helper scripts only. It grants no rights in source
scores, scans, annotations, or generated data.
