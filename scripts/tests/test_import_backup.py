import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]))
spec = importlib.util.spec_from_file_location("import_backup", Path(__file__).parents[1] / "data-transfer.py")
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class ImportBackupTests(unittest.TestCase):
    def test_import_media_required_and_missing_file_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = {"tables": {"import_batch": {"rows": [["package"]]},
                                   "audio_asset": {"columns": [], "rows": []}}}
            with self.assertRaises(ValueError):
                backup.content_files(root, payload, "snapshot")
            (root / "content").mkdir()
            content = b"original-test-material"
            (root / "content/source.txt").write_bytes(content)
            manifest = {"snapshotSha256": "snapshot", "files": [{"path": "source.txt",
                "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}]}
            raw = json.dumps(manifest).encode()
            (root / "content-manifest.json").write_bytes(raw)
            (root / "CONTENT_COMPLETE").write_text(hashlib.sha256(raw).hexdigest())
            payload["tables"]["import_batch"] = {"rows": [], "columns": []}
            self.assertEqual(len(backup.content_files(root, payload, "snapshot")), 1)
            (root / "content/source.txt").write_text("corrupted")
            with self.assertRaises(ValueError):
                backup.content_files(root, payload, "snapshot")

    def test_content_marker_and_database_reference_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = {"tables": {"audio_asset": {"columns": ["status", "storage_key", "sha256"],
                "rows": [["ready", "missing.mp3", "a" * 64]]}}}
            raw = json.dumps({"snapshotSha256": "snapshot", "files": []}).encode()
            (root / "content-manifest.json").write_bytes(raw)
            with self.assertRaises(ValueError):
                backup.content_files(root, payload, "snapshot")
            (root / "CONTENT_COMPLETE").write_text(hashlib.sha256(raw).hexdigest())
            with self.assertRaises(ValueError):
                backup.content_files(root, payload, "snapshot")


if __name__ == "__main__":
    unittest.main()
