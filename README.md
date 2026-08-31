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

The R2 S3 endpoint in the lockfile is the immutable object location, not a browser-public
origin. Until its public R2.dev/custom-domain URL is enabled, pass that origin explicitly:
`make extract-source ARCHIVE_BASE_URL=https://archives.example.org`.

## Build from scratch

```bash
git clone https://github.com/jhlusko/ossq-omr-data.git
cd ossq-omr-data

make extract-source
make check-inputs
```

The extracted archive reproduces the exact source input to the historical build. The
crop/label transformation itself has not yet been moved here; do not call a new corpus
reproduction complete until that executable pipeline is vendored and its output digest is
recorded. The included `tools/package_dataset.py` can verify any materialized portable
dataset without importing HOMR.

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
