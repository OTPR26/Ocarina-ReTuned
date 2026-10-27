import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/native'))
from player_models.export import prepared_models
from prepare_ui_assets import RomFs
import test_ui_assets as fixtures


class PlayerModelExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'installation'
        self.root.mkdir()
        (self.root / 'romfs.bin').write_bytes(fixtures.NativeRomFsTests().fixture())
        self.manifest = {'source': {'romfs_image_path': str(self.root / 'romfs.bin')},
                         'texture_hash_aliases': [{'native': 1, 'original': 2, 'modern': True}]}
        (self.root / 'process-manifest.json').write_text(json.dumps(self.manifest))
        (self.root / 'code.bin').write_bytes(b'code fixture')
        (self.root / 'triaevum_title_aot.dylib').write_bytes(b'unchanged module')
        self.converter = Mock(return_value=(b'MODEL', {'source_name': 'test model'}))
        mocked = patch.dict(sys.modules, {'player_models.convert': SimpleNamespace(convert_actor=self.converter)})
        mocked.start(); self.addCleanup(mocked.stop)
        actors = patch.dict('player_models.export.ACTORS', {'child': 'a'}, clear=True)
        actors.start(); self.addCleanup(actors.stop)

    def test_export_keeps_source_module_and_texture_mappings(self):
        original = (self.root / 'romfs.bin').read_bytes()
        with prepared_models(self.root, child='child.pak') as output:
            self.assertNotEqual(output, self.root)
            self.assertEqual(RomFs(output / 'romfs.bin').read('a'), b'MODEL')
            document = json.loads((output / 'process-manifest.json').read_text())
            self.assertEqual(document['texture_hash_aliases'], self.manifest['texture_hash_aliases'])
            self.assertEqual(document['source']['romfs_service_size'], (output / 'romfs.bin').stat().st_size)
            self.assertEqual(document['exported_player_models']['child']['name'], 'test model')
            self.assertEqual((output / 'triaevum_title_aot.dylib').read_bytes(), b'unchanged module')
        self.assertFalse(output.exists())
        self.assertEqual((self.root / 'romfs.bin').read_bytes(), original)
        self.assertEqual(list(self.root.parent.iterdir()), [self.root])

    def test_without_models_uses_existing_preparation(self):
        with prepared_models(self.root) as output:
            self.assertEqual(output, self.root)
        self.converter.assert_not_called()

    def test_failed_conversion_preserves_original(self):
        self.converter.side_effect = ValueError('Unsupported rig')
        before = (self.root / 'romfs.bin').read_bytes()
        with self.assertRaises(ValueError), prepared_models(self.root, child='unsupported.pak'):
            self.fail('Must not yield failed conversion')
        self.assertEqual((self.root / 'romfs.bin').read_bytes(), before)
        self.assertEqual(list(self.root.parent.iterdir()), [self.root])

    def test_export_failure_cleans_only_temporary_output(self):
        with self.assertRaises(RuntimeError):
            with prepared_models(self.root, child='child.pak') as output:
                raise RuntimeError('Signing or SD export failed')
        self.assertFalse(output.exists())
        self.assertTrue((self.root / 'romfs.bin').exists())
