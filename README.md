# OSSQ-OMR data build

Code and instructions for reconstructing a portable HOMR Stage-2 OSSQ dataset from
the upstream OpenScore String Quartets material. This repository deliberately contains
**no scanned images, PDFs, MuseScore source files, trained weights, or generated crop
payloads**. Obtain each source under its own terms before running the build.

The resulting dataset is designed for a clean consumer: materialized images, relative
index paths, score-disjoint splits, notation sidecars, and a manifest digest. It is not
a replacement for the upstream OSSQ repository or its licence/provenance notices.

## Inputs

1. An authorised checkout of `MALerLab/ossq-omr`.
2. A checkout of `MALerLab/omr-data-preprocessor` for the source crawl/conversion
   stages.
3. MuseScore CLI, Python dependencies, and the YOLO weights required by the upstream
   preprocessor.

## Build from scratch

```bash
git clone https://github.com/MALerLab/ossq-omr-data.git
cd ossq-omr-data

export OSSQ_SOURCE=/absolute/path/to/ossq-omr
export PREPROCESSOR_SOURCE=/absolute/path/to/omr-data-preprocessor
export OUT=/absolute/path/to/ossq-omr-build

make check-inputs
make preprocess
make package
make verify
```

`preprocess` is intentionally an explicit hand-off to the numbered upstream pipeline:
it requires the operator to review source terms and run its crawl/download stages before
deriving images. `package` uses this repository's vendored portable-package verifier;
it never rewrites a source checkout in place.

## Release gates

- Preserve a per-work provenance table: upstream revision, scan URL, rights assertion,
  and every derived crop ID.
- Keep train/validation score-disjoint and test the assertion after packaging.
- Do not publish scans until their source rights are independently verified.
- Run a fresh-clone consumer test and `--verify-only` against the packaged tree before
  uploading it to a dataset host.

The expected host layout and card requirements should ship with every dataset release.

## License

MIT for this build documentation and helper scripts only. It grants no rights in source
scores, scans, annotations, or generated data.
