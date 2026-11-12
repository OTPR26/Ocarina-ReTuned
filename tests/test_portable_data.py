from pathlib import Path
import importlib.util
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('portable_data', Path(__file__).resolve().parents[1] / 'tools/native/portable_data.py')
portable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(portable)


class PortableDataTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / 'AppData/Game'
        self.app = self.root / 'App folder'
        self.app.mkdir()
        self.source.mkdir(parents=True)
        (self.source / 'saves').mkdir()
        (self.source / 'saves/slot.bin').write_bytes(b'player progress\x00\xff')
        self.profile = {'arguments': ['--save-data', str(self.source / 'saves'), '--title-plugin', str(self.source / 'title.dll'), '--resource-root', str(self.app)], 'external': str(self.root / 'Textures')}
        (self.source / 'native-launch.json').write_text(json.dumps(self.profile))
        (self.source / 'title.dll').write_bytes(b'prepared module')

    def test_verified_copy_and_relocation_keep_saves_and_external_paths(self):
        before = portable.inventory(self.source)
        destination = portable.migrate(self.source, self.app)
        self.assertEqual(portable.inventory(self.source), before)
        self.assertEqual((destination / 'saves/slot.bin').read_bytes(), b'player progress\x00\xff')
        profile = json.loads((destination / 'native-launch.json').read_text())
        self.assertEqual(Path(profile['arguments'][1]), destination / 'saves')
        self.assertEqual(profile['external'], self.profile['external'])
        moved = self.root / 'Different disk'
        self.app.rename(moved)
        portable.relocate(moved)
        profile = json.loads((moved / 'user/native-launch.json').read_text())
        self.assertEqual(Path(profile['arguments'][1]), moved / 'user/saves')
        self.assertEqual(Path(profile['arguments'][5]), moved)
        self.assertEqual(profile['external'], self.profile['external'])
        before = portable.inventory(moved)
        portable.relocate(moved)
        self.assertEqual(before, portable.inventory(moved))

    def test_existing_destination_is_never_overwritten(self):
        (self.app / 'user').mkdir()
        (self.app / 'user/keep').write_text('existing data')
        with self.assertRaises(ValueError):
            portable.migrate(self.source, self.app)
        self.assertEqual((self.app / 'user/keep').read_text(), 'existing data')

    def test_copy_corruption_never_activates(self):
        original = shutil.copytree
        def corrupt(source, destination, *args, **kwargs):
            original(source, destination, *args, **kwargs)
            if Path(source) != self.source:
                return
            (Path(destination) / 'saves/slot.bin').write_bytes(b'bad')
        with patch.object(portable.shutil, 'copytree', corrupt):
            with self.assertRaises(ValueError):
                portable.migrate(self.source, self.app)
        self.assertFalse((self.app / 'user').exists())
        self.assertFalse(list(self.app.glob('.portable-copy-*')))

    def test_low_disk_space_keeps_original(self):
        before = portable.inventory(self.source)
        with patch.object(portable.shutil, 'disk_usage', return_value=shutil._ntuple_diskusage(1, 1, 0)):
            with self.assertRaises(ValueError):
                portable.migrate(self.source, self.app)
        self.assertEqual(before, portable.inventory(self.source))
        self.assertFalse((self.app / 'user').exists())

    def test_links_are_rejected(self):
        (self.source / 'linked').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            portable.migrate(self.source, self.app)
        self.assertFalse((self.app / 'user').exists())

    def test_windows_paths_respect_component_boundaries(self):
        mapping = [('C:\\Users\\Player\\Game', 'D:/Portable/user')]
        self.assertEqual(portable.remap('c:\\users\\player\\game\\saves', mapping), 'D:/Portable/user/saves')
        self.assertEqual(portable.remap('C:/Users/Player/Game-other/saves', mapping), 'C:/Users/Player/Game-other/saves')

    def test_interrupted_relocation_resumes(self):
        portable.migrate(self.source, self.app)
        moved = self.root / 'Moved'
        self.app.rename(moved)
        root = moved / 'user'
        (root / 'native-launch.json.portable-new').write_text('interrupted')
        portable.relocate(moved)
        self.assertFalse((root / 'native-launch.json.portable-new').exists())
        self.assertEqual(json.loads((root / 'portable.json').read_text())['data_root'], str(root))

    def test_app_file_update_preserves_portable_data(self):
        (self.app / 'OcarinaReTuned.exe').write_bytes(b'old host')
        destination = portable.migrate(self.source, self.app)
        (destination / 'settings.json').write_text('{"volume": 65}')
        before = portable.inventory(destination)
        update = self.root / 'update'
        (update / 'setup').mkdir(parents=True)
        (update / 'OcarinaReTuned.exe').write_bytes(b'new host')
        (update / 'setup/portable_data.py').write_text('new helper')
        shutil.copytree(update, self.app, dirs_exist_ok=True)
        portable.relocate(self.app)
        self.assertEqual(portable.inventory(destination), before)
        self.assertEqual((self.app / 'OcarinaReTuned.exe').read_bytes(), b'new host')

    def test_interrupted_copy_keeps_source_and_can_retry(self):
        before = portable.inventory(self.source)
        original = shutil.copytree
        def interrupted(source, destination, *args, **kwargs):
            original(source, destination, *args, **kwargs)
            raise OSError('copy interrupted')
        with patch.object(portable.shutil, 'copytree', interrupted):
            with self.assertRaises(OSError):
                portable.migrate(self.source, self.app)
        self.assertEqual(portable.inventory(self.source), before)
        self.assertFalse((self.app / 'user').exists())
        self.assertFalse(list(self.app.glob('.portable-copy-*')))
        portable.migrate(self.source, self.app)
        self.assertEqual((self.app / 'user/saves/slot.bin').read_bytes(), b'player progress\x00\xff')

    def test_partial_relocation_retries_after_replace_failure(self):
        destination = portable.migrate(self.source, self.app)
        (destination / 'a-settings.json').write_text(json.dumps({'saves': str(destination / 'saves')}))
        old_marker = (destination / 'portable.json').read_bytes()
        moved = self.root / 'Moved with spaces'
        self.app.rename(moved)
        root = moved / 'user'
        original = portable.os.replace
        def interrupted(source, destination):
            if Path(destination).name == 'native-launch.json':
                raise OSError('replace interrupted')
            return original(source, destination)
        with patch.object(portable.os, 'replace', interrupted):
            with self.assertRaises(OSError):
                portable.relocate(moved)
        self.assertEqual((root / 'portable.json').read_bytes(), old_marker)
        self.assertEqual(json.loads((root / 'a-settings.json').read_text())['saves'], str(root / 'saves').replace('\\', '/'))
        portable.relocate(moved)
        profile = json.loads((root / 'native-launch.json').read_text())
        self.assertEqual(Path(profile['arguments'][1]), root / 'saves')
        self.assertEqual((root / 'saves/slot.bin').read_bytes(), b'player progress\x00\xff')
        self.assertFalse(list(root.rglob('*.portable-new')))
