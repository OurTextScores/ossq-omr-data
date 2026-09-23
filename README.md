# OSSQ-OMR data build

Code and provenance for reconstructing a portable HOMR Stage-2 OSSQ dataset from a
frozen OpenScore String Quartets source snapshot. This repository deliberately contains
**no scans, PDFs, MuseScore source files, trained weights, or generated crop payloads**;
the locked source archive is fetched separately and verified before extraction.

The resulting dataset is designed for a clean consumer: materialized images, relative
index paths, score-disjoint splits, notation sidecars, and a manifest digest. It is not
a replacement for the upstream OSSQ repository or its licence/provenance notices.

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
