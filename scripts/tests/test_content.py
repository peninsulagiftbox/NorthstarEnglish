import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('content_extract', Path(__file__).parents[1] / 'extract-demo.py')
content = importlib.util.module_from_spec(spec)
spec.loader.exec_module(content)


class ContentSafetyTest(unittest.TestCase):
    def test_literal_parser_rejects_executable_expressions(self):
        self.assertEqual([{'key': 'value', 'point': 5}], content.literal_array("const SAMPLE=[{key:'value',point:5}];", 'SAMPLE'))
        with self.assertRaises((ValueError, SyntaxError)):
            content.literal_array("const SAMPLE=[__import__('os').system('false')];", 'SAMPLE')

    def test_frozen_write_refuses_changed_existing_version(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'lesson.json'
            content.write_frozen(path, b'original')
            content.write_frozen(path, b'original')
            with self.assertRaises(ValueError):
                content.write_frozen(path, b'replacement')
            self.assertEqual(b'original', path.read_bytes())
