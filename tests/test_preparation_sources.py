"""Preparation kits retain structural boundaries, not original annotation text."""
import csv
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/native'))
spec = importlib.util.spec_from_file_location('preparation_sources', ROOT / 'tools/native/stage_preparation_sources.py')
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


class StructuralMetadata(unittest.TestCase):
    def test_strip_annotations_preserves_columns_and_boundaries(self):
        with tempfile.TemporaryDirectory() as temporary:
            original = Path(temporary) / 'source.csv'
            output = Path(temporary) / 'sanitized.csv'
            original.write_text('entry,size,name,evidence,notes\n0x1000,4,function,original instruction summary,original string text\n')
            source.sanitize_csv(original, output, {'entry', 'size', 'name'})
            with output.open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(rows, [{'entry': '0x1000', 'size': '4', 'name': 'function',
                'evidence': 'reviewed_entry_boundary', 'notes': ''}])
            self.assertNotIn('original', output.read_text())
            self.assertIn('original string text', original.read_text())

    def test_changed_schema_does_not_silently_drop_boundaries(self):
        with tempfile.TemporaryDirectory() as temporary:
            original = Path(temporary) / 'source.csv'
            original.write_text('name,notes\nfunction,annotation\n')
            with self.assertRaises(ValueError):
                source.sanitize_csv(original, Path(temporary) / 'output.csv', {'entry', 'size'})
