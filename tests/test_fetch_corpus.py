"""The digest check is the only thing standing between a corrupt download and training."""

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fetch_corpus", ROOT / "scripts" / "fetch_corpus.py")
fetch_corpus = importlib.util.module_from_spec(spec)
sys.modules["fetch_corpus"] = fetch_corpus
spec.loader.exec_module(fetch_corpus)


def _lock(tmp: Path, payload: bytes, *, sha: str | None = None) -> Path:
    lock = tmp / "lock.json"
    lock.write_text(
        json.dumps(
            {
                "corpus": {
                    "shards": [
                        {
                            "name": "valid-0000.tar.zst",
                            "url": "https://example.invalid/valid-0000.tar.zst",
                            "split": "valid",
                            "bytes": len(payload),
                            "sha256": sha or hashlib.sha256(payload).hexdigest(),
                        }
                    ]
                }
            }
        )
    )
    return lock


class TestVerify(unittest.TestCase):
    def test_a_matching_shard_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            payload = b"shard bytes"
            (tmp / "valid-0000.tar.zst").write_bytes(payload)
            self.assertEqual(
                fetch_corpus.fetch(_lock(tmp, payload), tmp, "valid", verify_only=True), 0
            )

    def test_a_tampered_shard_of_the_right_length_still_fails(self) -> None:
        # The length check alone would pass this: same size, different bytes. That is the
        # case a same-origin checksum file cannot protect against either.
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            payload = b"shard bytes"
            (tmp / "valid-0000.tar.zst").write_bytes(b"XXXXX bytes")
            self.assertEqual(
                fetch_corpus.fetch(_lock(tmp, payload), tmp, "valid", verify_only=True), 1
            )

    def test_an_absent_shard_is_a_failure_not_a_silent_pass(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self.assertEqual(
                fetch_corpus.fetch(_lock(tmp, b"shard bytes"), tmp, "valid", verify_only=True), 1
            )

    def test_an_unknown_split_raises_rather_than_reporting_success(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            with self.assertRaises(SystemExit):
                fetch_corpus.fetch(_lock(tmp, b"x"), tmp, "train", verify_only=True)


if __name__ == "__main__":
    unittest.main()
