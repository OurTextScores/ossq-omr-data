# Executable OSSQ Stage-2 build

`tools/build_ossq_stage2.py` is the complete source-to-HOMR-dataset path. It vendors:

- the MIT OSSQ preprocessor at commit `bdea0d1829c9db84480ebd2e0385f6f5fe324274`;
- its CC0 LMXE snapshot at `8c3b9fa3b328a144c82e5e7c583cfd329f10d88b`;
- a source-only HOMR Stage-2 runtime snapshot (AGPL-3.0; see `vendor/homr-stage2`).

The required external runtime tools are Python 3.10--3.12, MuseScore CLI (`mscore`),
and `requirements-build.txt` (install with `uv pip install -r requirements-build.txt`).
YOLO weights are fetched by the vendor's pinned upstream release mechanism on first use;
they are not source data and are not committed here.

For a cheap integrity smoke build, provide a one-score text file and use synthetic
rendering first:

```bash
make extract-source
python3 tools/build_ossq_stage2.py --score-list one-score.txt --tracks synthetic \
  --out build/ossq --device cpu
```

The output has one materialized dataset directory per `track/split`, each with PNG,
tokens, structured-notation sidecars, and `index.txt`. The converter refuses empty
split outputs, mismatched crop/part counts, and absent scanned systemwise MusicXML.
That fail-closed behavior is intentional: a shifted staff label is worse than a skipped
example.

## Rasterization reproducibility

Direct MuseScore PNG exports must be composited onto white paper before dropping
alpha. MuseScore 3.6.2 can write black RGB everywhere and encode all visible ink in
the alpha channel; a plain OpenCV colour read then produces an entirely black page.
Partial alpha must also be composited to preserve antialiased edges.

The vendored HOMR `musescore_boxes.render` now does this explicitly. The Stage-2
builder runs `tools/check_rasterization.py` before building; the check exercises the
actual render function with a transparent PNG fixture, preserves opaque colour
pixels, and verifies the patch hashes. Run it independently with
`make check-rasterization` in the build Python environment.

`vendor/RASTERIZATION_PATCH.json` records the patch checksum and each affected
file's before/after hashes; `vendor/patches/white-png-background.patch` contains the
exact change. These are overlays on the existing snapshots, not claims that the
base upstream commits already contained the fix. Preserve or incorporate the fix
when refreshing the vendored runtime and regenerate its provenance deliberately.

The default staff-crop builds rasterize PDFs rather than using this direct PNG
path. This fix alone does not establish corruption in existing published crops or
require rebuilding them. A fresh reproduction should still inspect actual pages
and record renderer/library versions; the fixture check does not prove a complete
external renderer installation works.

The OSSQ preprocessor’s direct-PNG helper also composites partial alpha and
accepts already-opaque images. The normal synthetic build remains MuseScore → PDF → PNG.
