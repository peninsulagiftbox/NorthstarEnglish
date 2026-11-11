import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("content_source", Path(__file__).parents[1] / "content_source.py")
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


class SourceTests(unittest.TestCase):
    def test_extract_and_review_preserves_raw_and_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "lesson.txt").write_text("Nora waits beside the door.\n")
            candidate = source.extract(root, "lesson.txt")
            self.assertEqual(candidate["status"], "unreviewed")
            reviewed = source.review(candidate, "Nora stands beside the door.\n", "human-test-input", "Correct verb", "confirmed")
            self.assertEqual(candidate["revision"], 0)
            self.assertEqual(reviewed["rawTranscript"], candidate["rawTranscript"])
            self.assertEqual(reviewed["revision"], 1)
            self.assertIn("+Nora stands", reviewed["audit"][0]["diff"])
            self.assertNotEqual(reviewed["correctedSha256"], candidate["correctedSha256"])

    def test_file_boundaries_and_encoding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bad.txt").write_bytes(b"\xff")
            (root / "wrong.pdf").write_text("not a PDF")
            (root / "outside").symlink_to("/etc/hosts")
            for name in ["../secret", "/etc/hosts", "outside", "wrong.pdf", "bad.txt"]:
                with self.assertRaises((ValueError, OSError)):
                    source.inspect(root, name)

    def test_transcript_preserves_internal_spacing(self):
        self.assertEqual(source.transcript([" e\u0301\r\n"]), source.transcript(["é"]))
        self.assertNotEqual(source.transcript(["a b"]), source.transcript(["a  b"]))


if __name__ == "__main__":
    unittest.main()
