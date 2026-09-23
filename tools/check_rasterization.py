#!/usr/bin/env python3
"""Check vendored rasterization patches and exercise transparent MuseScore PNG exports."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor/homr-stage2'))
from training.omr_datasets import musescore_boxes


class RasterizationChecks(unittest.TestCase):
    def test_patch_provenance(self):
        manifest = json.loads((ROOT / 'vendor/RASTERIZATION_PATCH.json').read_text())
        digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(digest(ROOT / manifest['patch']), manifest['sha256'])
        for name, hashes in manifest['files'].items():
            self.assertEqual(digest(ROOT / name), hashes['after_sha256'], name)

    def test_render_composites_white_paper_and_antialiased_ink(self):
        # MuseScore can encode the entire score in alpha, with RGB black everywhere.
        rgba = np.zeros((1, 3, 4), dtype=np.uint8)
        rgba[0, :, 3] = [0, 128, 255]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            score = root / 'sample.musicxml'
            score.write_text('<score-partwise><part-list/></score-partwise>')

            def export(command, **kwargs):
                target = Path(command[command.index('--export-to') + 1])
                target = target.with_name(target.stem + '-1' + target.suffix)
                if target.suffix == '.png':
                    self.assertTrue(cv2.imwrite(str(target), rgba))
                else:
                    target.write_text('<svg viewBox="0 0 3 1"/>')
                return SimpleNamespace(returncode=0, stderr='')

            with patch.object(musescore_boxes.subprocess, 'run', side_effect=export):
                _, pngs = musescore_boxes.render(score, root / 'out')
            image = cv2.imread(str(pngs[0]), cv2.IMREAD_UNCHANGED)
            np.testing.assert_array_equal(image, [[[255]*3, [127]*3, [0]*3]])

    def test_opaque_colour_pixels_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'opaque.png'
            image = np.array([[[12, 70, 210], [255, 255, 255]]], dtype=np.uint8)
            cv2.imwrite(str(path), image)
            original = path.read_bytes()
            musescore_boxes.flatten_png_background(path)
            self.assertEqual(path.read_bytes(), original)

    def test_ossq_direct_png_helper(self):
        path = ROOT / 'vendor/ossq-preprocessor/omrdp/utils/image.py'
        if not path.exists():
            self.skipTest('OSSQ preprocessor is not part of the Lieder repo')
        spec = importlib.util.spec_from_file_location('ossq_image', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        rgba = np.array([[[0, 0, 0, 0], [0, 0, 0, 128], [12, 70, 210, 255]]], dtype=np.uint8)
        np.testing.assert_array_equal(module.make_background_white(rgba),
                                      [[[255]*3, [127]*3, [12, 70, 210]]])
        bgr = rgba[:, :, :3].copy()
        np.testing.assert_array_equal(module.make_background_white(bgr), bgr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
