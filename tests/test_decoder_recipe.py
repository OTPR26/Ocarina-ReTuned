"""Decoder source identity and existing build output are never bypassed."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('decoder_recipe', ROOT / 'tools/native/build_android_capstone.py')
recipe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recipe)


class DecoderRecipe(unittest.TestCase):
    def test_modified_source_is_rejected_before_creating_output(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(recipe.sys, 'platform', 'linux'):
            root = Path(temporary)
            source = root / 'source.tar.gz'
            source.write_bytes(b'wrong source')
            with self.assertRaisesRegex(ValueError, 'original Capstone'):
                recipe.build(source, root / 'ndk', root / 'output')
            self.assertFalse((root / 'output').exists())

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(recipe.sys, 'platform', 'linux'):
            root = Path(temporary)
            source = root / 'source.tar.gz'
            source.write_bytes(b'fixture')
            output = root / 'output'
            output.mkdir()
            (output / 'keep').write_text('existing build')
            with patch.object(recipe, 'SOURCE_SHA256', hashlib.sha256(source.read_bytes()).hexdigest()):
                with self.assertRaisesRegex(ValueError, 'existing output'):
                    recipe.build(source, root / 'ndk', output)
            self.assertEqual((output / 'keep').read_text(), 'existing build')
