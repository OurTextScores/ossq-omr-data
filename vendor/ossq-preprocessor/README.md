# omr-data-preprocessing

Data-preprocessing pipeline that builds the **OSSQ-OMR** dataset for Optical Music Recognition (OMR) research from the OpenScore String Quartets corpus. It crawls and downloads scanned/synthetic string-quartet scores, converts them between symbolic music formats (MusicXML, LMXE, **kern, ABC), and produces the cropped/aligned systemwise and partwise image + symbolic pairs used to train and evaluate OMR models.

This repo is one piece of a larger release; if you're new here, start at the **[string-quartet-omr-benchmark](https://github.com/MALerLab/string-quartet-omr-benchmark)** umbrella repository, which links the dataset, this pipeline, the LMXE format library, and the model training/eval code.

## Part of the String Quartet OMR Benchmark

> **A Dataset and Benchmark for Optical Music Recognition of String Quartet Scores**<br>
> Dongmin Kim, Brian Liu, Jose J. Valero-Mas, Dasaem Jeong<br>
> *Proceedings of the 27th International Society for Music Information Retrieval Conference (ISMIR), 2026*

This repository holds the preprocessing pipeline that builds the OSSQ-OMR dataset's derived symbolic formats.

- **[string-quartet-omr-benchmark](https://github.com/MALerLab/string-quartet-omr-benchmark)**: umbrella entry point for the paper and the full repository constellation.
- **[ossq-omr](https://github.com/MALerLab/ossq-omr)**: the OSSQ-OMR dataset — MuseScore/MusicXML annotation sources and their revision history.
- **[omr-data-preprocessor](https://github.com/MALerLab/omr-data-preprocessor)**: the preprocessing pipeline that builds every derived symbolic format from the dataset sources. *(this repository)*
- **[sqomr](https://github.com/MALerLab/sqomr)**: model training and evaluation experiments.
- **[lmxe](https://github.com/MALerLab/lmxe)**: the LMXE symbolic format library (derived from [OMR-Research/lmx](https://github.com/OMR-Research/lmx)).

## Setup

```bash
git clone --recursive git@github.com:MALerLab/omr-data-preprocessor.git
cd omr-data-preprocessor
uv sync
```

If you already cloned without `--recursive`, run `git submodule update --init --recursive`.

- The **[lmxe](https://github.com/MALerLab/lmxe)** symbolic-format library is vendored as a git submodule at `modules/lmxe`, providing the LMXE (Linear MusicXML Encoding) format and MusicXML delinearization/conversion utilities used throughout the pipeline.
- Python `>=3.10,<3.11` (pinned via `.python-version` to `3.10.12`), managed with `uv`.
- Key dependencies (see `pyproject.toml`): `music21`, `converter21`, `kernpy`, `musicdiff`, `Levenshtein`, `zss`, `ultralytics` (YOLO), `opencv-python`, `pdfplumber`, `beautifulsoup4`/`lxml`/`requests` (crawling).

See [Requirements](#requirements) below for external dependencies not covered by `uv sync`.

## Requirements

These are easy to miss since they aren't installed by `uv sync` or aren't on PyPI under the expected name:

- **MuseScore CLI (`mscore`)** — must be installed and on `PATH`. It is invoked via `subprocess` in `omrdp/utils/musescore.py` (`cmd = ['mscore', ...]`) for MuseScore→MusicXML conversion and for rendering synthetic score PDFs.
- **`kernpy`** — pulled from the fork **[`halsoo/kernpy@sq-fix`](https://github.com/halsoo/kernpy/tree/sq-fix)** (not the upstream PyPI package) via `[tool.uv.sources]` in `pyproject.toml`; `uv sync` resolves this automatically, no manual step needed.
- **YOLO checkpoint weights** — no manual setup needed. The system/staff-detection steps (`omrdp/ossq/yolo_detect_systems.py`, `yolo_detect_staves.py`, `yolo_detect_staff_heights.py`) load `.pt` weights from a gitignored `checkpoints/` directory at the repo root; `omrdp/utils/yolo.py` downloads any missing checkpoint automatically from the [MALerLab/ls-yolo](https://github.com/MALerLab/ls-yolo) releases on first use (so the first run needs network access).

## Package layout (`omrdp/`)

- `ossq/` — the OSSQ pipeline scripts invoked by the `ossq_*.sh` entry points (crawling, format conversion, cropping, alignment, cleaning).
- `utils/` — shared helpers (image ops, bounding boxes, MuseScore invocation, YOLO wrappers, symbolic-format constants).

## Data root

Every entry script declares an empty `BASE_DIR` variable on line 2 and passes it to each Python module via `-d $BASE_DIR`. All `ossq_*.sh` scripts read from and write into this directory, so **set `BASE_DIR` to your local checkout of the [ossq-omr](https://github.com/MALerLab/ossq-omr) dataset repo before running any script** — for example:

```sh
BASE_DIR=/path/to/ossq-omr/
```

The scripts ship with it blank on purpose, so nothing runs against an unintended directory; set it in each script you plan to run (or export it in your shell and delete the assignment). Most step scripts also support a commented-out `--list-path` option to scope a run to a subset of works via a task-list text file.

## Pipeline overview

Run the scripts in this order against a checkout of the dataset repo:

1. **`ossq_crawl_ismlp.sh`** — crawls IMSLP for score metadata and PDF URLs for each string quartet entry, writing results into the dataset repo's metadata (calls `omrdp/ossq/crawl_imslp.py -c 1`).
2. **`ossq_download_pdfs.sh`** — downloads the scanned score PDFs referenced in the crawled metadata (calls the same `crawl_imslp.py` with `-c 0`).
3. **`ossq_step_001.sh`** — converts MuseScore source files to MusicXML and cleans them; converts MusicXML to systemwise LMXE; renders synthetic per-system and per-part score images from MuseScore (PDF → images) and crops/resizes them via YOLO system/staff detection; also crops the scanned PDFs into systemwise/partwise images.
4. **`ossq_step_002.sh`** — aligns systemwise LMXE against the cropped synthetic/scanned system images, splits systemwise LMXE into partwise LMXE, and aligns the partwise LMXE against the cropped part images.
5. **`ossq_step_003.sh`** — generates part-by-part LMXE (PLMXE, follows partwise MusicXML structure, systemwise only) and reduced LMXE (RLMXE, stem directions and time signatures stripped, systemwise and partwise) variants from LMXE (`convert_lmxe_to_variant.py`).
6. **`ossq_step_004.sh`** — converts MusicXML to **kern and then to extended-kern (eKern), splits **kern into partwise form, and aligns the partwise **kern against the corresponding images.
7. **`ossq_step_005.sh`** — converts MusicXML to ABC notation, cleans it, converts to extended-ABC (eABC), and repeats the split/clean/align/convert-to-eABC steps at the partwise level.
8. **`ossq_process_symbolic_systemwise_rlmxe.sh`** — a standalone symbolic-only helper for (re-)generating systemwise RLMXE from LMXE via `convert_lmxe_to_rlmxe.py`, independent of the numbered step scripts (currently a stub with the conversion call commented out).
9. **`ossq_clean.sh`** — deletes intermediate/generated files under a given relative path inside `BASE_DIR` (e.g. `temp`, `lmxe/...`, `musicxml/...`, `images/...`); the target path is set via the `--path` argument, with common paths listed as commented-out alternatives in the script.

## Derived formats

Running the numbered pipeline above against a git checkout of [ossq-omr](https://github.com/MALerLab/ossq-omr) reproduces the derived symbolic and image formats that ship alongside OSSQ-OMR, starting from the MuseScore source files and scanned PDFs tracked in that repo.

Format family produced by each step:

- **LMXE**, systemwise — step 001; **LMXE**, partwise — step 002 (split from systemwise)
- **PLMXE**, systemwise only, and **RLMXE**, systemwise + partwise — step 003
- **\*\*kern / eKern**, systemwise + partwise — step 004
- **ABC / eABC**, systemwise + partwise — step 005
- Cropped systemwise/partwise **images** (synthetic + scanned) — step 001, refined by alignment in steps 002/004/005

## Citation

If you use this pipeline or the OSSQ-OMR dataset, please cite:

```bibtex
@inproceedings{Kim2026sqomrbench,
    title     = {A Dataset and Benchmark for Optical Music Recognition of String Quartet Scores},
    author    = {Dongmin Kim and Brian Liu and Jose J. Valero-Mas and Dasaem Jeong},
    year      = 2026,
    booktitle = {Proceedings of the 27th International Society for Music Information Retrieval Conference (ISMIR)},
}
```

This pipeline touches every one of the works below — LMXE and the Zeus model, the OpenScore String Quartets corpus, the SMT baseline, and the LEGATO baseline — so please cite them alongside the paper:

```bibtex
@inproceedings{mayer2024lmx,
    title     = {Practical End-to-End Optical Music Recognition for Pianoform Music},
    author    = {Mayer, Ji{\v{r}}{\'\i} and Straka, Milan and Haji{\v{c}} jr., Jan and Pecina, Pavel},
    year      = 2024,
    booktitle = {18th International Conference on Document Analysis and Recognition (ICDAR 2024)},
    pages     = {55--73},
    doi       = {10.1007/978-3-031-70552-6_4},
}
```

```bibtex
@inproceedings{gotham_openscore_2023,
    title     = {The “{OpenScore} {String} {Quartet}” {Corpus}},
    author    = {Mark R. H. Gotham and Maureen Redbond and Bruno Bower and Peter Jonas},
    year      = 2023,
    booktitle = {Proceedings of the 10th {International} {Conference} on {Digital} {Libraries} for {Musicology}},
    pages     = {49--57},
    publisher = {ACM},
    address   = {Milan Italy},
    copyright = {All rights reserved},
    isbn      = {9798400708336},
    language  = {en},
    urldate   = {2023-11-16},
    month     = nov,
    doi       = {10.1145/3625135.3625155},
    url       = {https://dl.acm.org/doi/10.1145/3625135.3625155},
}
```

```bibtex
@inproceedings{riosvila2024smt,
    title     = {Sheet Music Transformer: End-To-End Optical Music Recognition Beyond Monophonic Transcription},
    author    = {Ríos-Vila, Antonio and Calvo-Zaragoza, Jorge and Paquet, Thierry},
    year      = 2024,
    booktitle = {18th International Conference on Document Analysis and Recognition (ICDAR 2024)},
    pages     = {20--37},
    doi       = {10.1007/978-3-031-70552-6_2},
}
```

```bibtex
@inproceedings{yang2026legato,
    title     = {LEGATO: Large-scale End-to-end Generalizable Approach to Typeset OMR},
    author    = {Guang Yang and Victoria Ebert and Nazif Tamer and Brian Siyuan Zheng and Luiza Pozzobon and Noah A. Smith},
    year      = 2026,
    booktitle = {International Conference on Learning Representations (ICLR)},
    url       = {https://arxiv.org/abs/2506.19065},
}
```

## License

MIT. See `LICENSE`.
