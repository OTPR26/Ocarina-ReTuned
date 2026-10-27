import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/native'))
from player_models import install
from prepare_ui_assets import RomFs
import test_ui_assets as fixtures


class PlayerModelInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.rom = self.root / 'romfs.bin'; self.rom.write_bytes(fixtures.NativeRomFsTests().fixture())
        manifest = self.root / 'process-manifest.json'
        self.aliases = [{'native': 123, 'original': 456, 'modern': True}]
        manifest.write_text(json.dumps({'source': {'romfs_image_path': str(self.rom)},
                                        'texture_hash_aliases': self.aliases}))
        self.profile = self.root / 'native-launch.json'
        self.profile.write_text(json.dumps({'format': 'oot3d_native_game_launch_profile_v1', 'arguments': [
            '--a32-process-manifest', str(manifest), '--title-plugin', 'same-native-module', '--save-data', 'same-saves']}))
        actors = patch.dict(install.ACTORS, {'child': 'a'}, clear=True); actors.start(); self.addCleanup(actors.stop)
        # The converter is independently exercised against private child/adult fixtures.
        converter = patch.dict(sys.modules, {'player_models.convert': SimpleNamespace(convert_actor=Mock(return_value=(b'MODEL', {'triangles': 1})))})
        converter.start(); self.addCleanup(converter.stop)

    def test_import_restore_and_update_preserve_module_and_save_arguments(self):
        before = self.rom.read_bytes()
        install.change(self.root, age='child', package='data-only.pak')
        profile, _, manifest = install.profile_manifest(self.root)
        self.assertEqual(manifest['texture_hash_aliases'], self.aliases)
        self.assertEqual(profile['arguments'][2:], ['--title-plugin', 'same-native-module', '--save-data', 'same-saves'])
        self.assertEqual(RomFs(manifest['source']['romfs_image_path']).read('a'), b'MODEL')
        self.assertEqual(manifest['source']['romfs_image_file_size'], Path(manifest['source']['romfs_image_path']).stat().st_size)
        self.assertEqual(manifest['source']['romfs_service_size'], manifest['source']['romfs_image_file_size'])
        self.assertEqual(manifest['source']['romfs_service_offset'], 0)
        install.apply_to_preparation(self.root, self.rom, self.root / 'update.bin', manifest)
        self.assertEqual(RomFs(self.root / 'update.bin').read('a'), b'MODEL')
        install.change(self.root, age='child')
        _, _, restored = install.profile_manifest(self.root)
        self.assertEqual(restored['texture_hash_aliases'], self.aliases)
        self.assertEqual(restored['player_models'], {})
        self.assertEqual(RomFs(restored['source']['romfs_image_path']).read('a'), b'ROM!')
        self.assertEqual(self.rom.read_bytes(), before)
        self.assertIn('child', restored['available_player_models'])
        install.change(self.root, age='child', use_imported=True)
        _, _, selected = install.profile_manifest(self.root)
        self.assertEqual(selected['texture_hash_aliases'], self.aliases)
        self.assertEqual(RomFs(selected['source']['romfs_image_path']).read('a'), b'MODEL')
        images=list((self.root/'player-models').glob('*/romfs.bin'))
        self.assertEqual(len(images),2)
        self.assertEqual(install.read_actor(self.root,selected['player_models']['child'],'converted'),b'MODEL')

    def test_failed_activation_keeps_previous_profile_and_cleans_only_own_stage(self):
        before = self.profile.read_bytes()
        with patch.object(install.os, 'replace', side_effect=OSError('disk error')):
            with self.assertRaises(OSError): install.change(self.root, age='child', package='data-only.pak')
        self.assertEqual(self.profile.read_bytes(), before)
        self.assertEqual(list((self.root / 'player-models').iterdir()), [])
        self.assertFalse((self.root / '.rom-setup.lock').exists())

    def test_corrupted_model_is_not_reapplied(self):
        install.change(self.root, age='child', package='data-only.pak')
        _, _, manifest = install.profile_manifest(self.root)
        Path(manifest['player_models']['child']['converted']).write_bytes(b'BROKEN')
        with self.assertRaisesRegex(ValueError, 'integrity'):
            install.apply_to_preparation(self.root, self.rom, self.root / 'update.bin', manifest)
        self.assertFalse((self.root / 'update.bin').exists())
