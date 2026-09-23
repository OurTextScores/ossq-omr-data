#!/usr/bin/env python3
"""Build a HOMR-ready OSSQ staff-crop corpus from the locked source tree.

This is intentionally a small orchestration layer over the vendored, immutable
preprocessor snapshot and the vendored HOMR Stage-2 converter.  It never downloads
source scores or scans: those must already have passed ``make extract-source``.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREPROCESSOR = ROOT / "vendor" / "ossq-preprocessor"
STAGE2 = ROOT / "vendor" / "homr-stage2"


def run(module: str, *args: str, env: dict[str, str]) -> None:
    subprocess.run([sys.executable, "-m", module, *args], check=True, env=env)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "sources" / "ossq-source")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--tracks", choices=("synthetic", "scanned", "both"), default="both")
    parser.add_argument("--score-list", type=Path, help="Optional score-ID list for a smoke build.")
    parser.add_argument("--device", default="cpu", help="YOLO device, e.g. cuda:0 or cpu.")
    parser.add_argument("--skip-preprocess", action="store_true", help="Reuse existing crops/aligned MusicXML.")
    args = parser.parse_args()
    subprocess.run([sys.executable, str(ROOT / "tools/check_rasterization.py")], check=True)
    if not (args.source / "data" / "scores.yaml").is_file():
        raise SystemExit(f"not an extracted OSSQ source tree: {args.source}")
    if args.out.exists() and any(args.out.iterdir()):
        raise SystemExit(f"output must be empty or absent: {args.out}")
    args.out.mkdir(parents=True, exist_ok=True)
    # The upstream processor treats its log directory as pre-created source state;
    # source archives intentionally omit generated logs, so create it explicitly.
    (args.source / "logs").mkdir(exist_ok=True)

    env = os.environ.copy()
    env.setdefault("OMR_MUSESCORE", "xvfb-run -a mscore")
    env["PYTHONPATH"] = os.pathsep.join([str(PREPROCESSOR), str(STAGE2), env.get("PYTHONPATH", "")])
    tracks = ("synthetic", "scanned") if args.tracks == "both" else (args.tracks,)
    list_arg = ("--list-path", str(args.score_list)) if args.score_list else ()

    if not args.skip_preprocess:
        # Shared symbolic preparation, then the two image/crop tracks.  These are the
        # exact necessary stages from the original numbered OSSQ pipeline; unused
        # LMXE/kern/ABC variants are deliberately omitted.
        for module, extra in (
            ("omrdp.ossq.convert_musescore_to_musicxml", ("-d", str(args.source), "--multi-process", "1")),
            ("omrdp.ossq.clean_musicxml", ("-d", str(args.source), "--multi-process", "1", "-v", "0")),
            ("omrdp.ossq.convert_musicxml_to_lmxe", ("-d", str(args.source), "--multi-process", "1", "--remove-stem-direction", "1")),
        ):
            run(module, *extra, *list_arg, env=env)
        for track in tracks:
            common = ("-d", str(args.source), "-t", track)
            if track == "synthetic":
                run("omrdp.ossq.convert_musescore_to_pdf", *common, *list_arg, env=env)
            run("omrdp.ossq.convert_pdf_to_images", *common, *list_arg, env=env)
            run("omrdp.ossq.yolo_detect_systems", *common, "-n", "32", "--device", args.device, "--reproduce", "0", *list_arg, env=env)
            run("omrdp.ossq.yolo_crop_systems", *common, "--confidence-threshold", "0.45" if track == "synthetic" else "0.30", "--merge-threshold", "0.7", "--reproduce", "0", *list_arg, env=env)
            run("omrdp.ossq.yolo_detect_staff_heights", *common, "-n", "64", "--device", args.device, "--reproduce", "0", *list_arg, env=env)
            run("omrdp.ossq.yolo_resize_systems", *common, "--target_height", "18", "--reproduce", "0", *list_arg, env=env)
            run("omrdp.ossq.yolo_detect_staves", *common, "-n", "64", "--device", args.device, "--reproduce", "0", *list_arg, env=env)
            run("omrdp.ossq.yolo_crop_staves", *common, "--confidence-threshold", "0.7", "--merge-threshold", "0.7", "--reproduce", "0", *list_arg, env=env)
            run("omrdp.ossq.align_systems_lmxe", *common, *list_arg, env=env)

    for track in tracks:
        for split in ("train", "valid", "test_synth", "test_scanned"):
            destination = args.out / track / split
            try:
                run("training.omr_datasets.convert_ossq", "--dataset-root", str(args.source), "--out", str(destination), "--track", track, "--split", split, env=env)
            except subprocess.CalledProcessError:
                # A one-score smoke input intentionally has no examples in the other
                # score-disjoint splits.  A complete build must still fail closed if
                # any declared split is empty.
                if args.score_list:
                    destination.rmdir()
                    print(f"{track}/{split}: empty for requested smoke subset, skipped")
                    continue
                raise


if __name__ == "__main__":
    main()
