#!/usr/bin/env python3
"""Check the vendored stem patch is applied and has not been reverted.

The per-system MusicXML is what HOMR builds its notation sidecars from. Before this patch it
was written after strip_stem_directions(), which mutates the system in place, and every
<stem> in the corpus was lost - silently, because stems are an UNKNOWN-masked label and a
missing label trains nothing rather than failing. A reordering that reintroduces the bug
would pass every other check, so this one reads the source and asserts the order.
"""
import ast
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "vendor/STEM_PATCH.json").read_text())
TARGET = ROOT / next(iter(MANIFEST["files"]))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StemPatchChecks(unittest.TestCase):
    def test_patch_provenance(self):
        self.assertEqual(digest(ROOT / MANIFEST["patch"]), MANIFEST["sha256"])
        for path, hashes in MANIFEST["files"].items():
            self.assertEqual(digest(ROOT / path), hashes["after_sha256"], f"{path} drifted")

    def test_musicxml_is_written_before_stems_are_stripped(self):
        tree = ast.parse(TARGET.read_text())
        calls = [
            (node.lineno, node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, (ast.Attribute, ast.Name))
        ]
        delin = [line for line, name in calls if name == "delinearize_lmxe"]
        strip = [line for line, name in calls if name == "strip_stem_directions"]
        self.assertTrue(delin and strip, "expected both calls in the conversion loop")
        # The first delinearisation writes the per-system MusicXML; it must precede the strip.
        self.assertLess(min(delin), min(strip),
                        "per-system MusicXML is delinearised after stems are stripped")


if __name__ == "__main__":
    unittest.main(verbosity=2)
