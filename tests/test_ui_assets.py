import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location('prepare_ui_assets', Path(__file__).parents[1]/'tools/native/prepare_ui_assets.py')
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)


class NativeRomFsTests(unittest.TestCase):
    def fixture(self):
        data=bytearray(116)
        struct.pack_into('<10I',data,0,40,40,4,44,24,68,4,72,36,112)
        struct.pack_into('<6I',data,44,0,0xffffffff,0xffffffff,0,0xffffffff,0)
        struct.pack_into('<IIQQII',data,72,0,0xffffffff,0,4,0xffffffff,2)
        data[104:106]=b'a\0';data[112:116]=b'ROM!'
        return bytes(data)

    def test_rewrite_updates_only_local_output_and_preserves_source(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source';destination=Path(td)/'prepared';original=self.fixture();source.write_bytes(original)
            rom=assets.RomFs(source);self.assertEqual(rom.read('a'),b'ROM!')
            rom.write_replacements(destination,{'a':b'prepared user resource'})
            self.assertEqual(assets.RomFs(destination).read('a'),b'prepared user resource')
            self.assertEqual(source.read_bytes(),original)
            with self.assertRaises(ValueError):rom.write_replacements(source,{'a':b'bad'})
            with self.assertRaises(ValueError):rom.write_replacements(destination,{'a':b'bad'})
            self.assertFalse(list(Path(td).glob('*.partial')))

    def test_malformed_payload_cannot_escape_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            data=bytearray(self.fixture());struct.pack_into('<Q',data,88,100000)
            path=Path(td)/'bad';path.write_bytes(data)
            with self.assertRaises(ValueError):assets.RomFs(path)

    def test_interrupted_output_is_preserved_on_exclusive_creation_failure(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source';source.write_bytes(self.fixture())
            destination=Path(td)/'prepared'
            partial=Path(td)/'prepared.partial';partial.write_bytes(b'previous interrupted data')
            with self.assertRaises(FileExistsError):
                assets.RomFs(source).write_replacements(destination,{'a':b'new resource'})
            self.assertEqual(partial.read_bytes(),b'previous interrupted data')
            self.assertFalse(destination.exists())


class BundledUiTests(unittest.TestCase):
    def test_shared_hud_atlas_reaches_localized_menus_without_replacing_text(self):
        replacements = {'menu/02_EU_ENGLISH/hud_all00.ctxb': b'ReFramed HUD',
                        'message/eu/eu.qm': b'multilingual messages',
                        'message/eu/ltn16.qbf': b'Latin font'}
        files = {name: (0, 0, 1) for name in replacements}
        files.update({'menu/08_EU_ITALIAN/hud_all00.ctxb': (0, 0, 100),
                      'menu/03_EU_GERMAN/hud_all00.ctxb': (0, 0, 100),
                      'menu/00_JP_JAPANESE/hud_all00.ctxb': (0, 0, 0),
                      'menu/common/hud_all00.ctxb': (0, 0, 100),
                      'menu/08_EU_ITALIAN/menu_file_select_parts00.ctxb': (0, 0, 100)})
        result = assets.localized_menu_resources(replacements, files)
        self.assertEqual(set(result) - set(replacements), {
            'menu/08_EU_ITALIAN/hud_all00.ctxb', 'menu/03_EU_GERMAN/hud_all00.ctxb'})
        self.assertEqual(result['menu/08_EU_ITALIAN/hud_all00.ctxb'], b'ReFramed HUD')
        self.assertEqual(result['message/eu/eu.qm'], b'multilingual messages')

    def setUp(self):
        import tempfile
        import hashlib
        import json
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.contract = self.root / 'contract.json'
        def record(data):
            return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        self.payload = {'romfs/a': b'intended UI', 'licenses/NOTICE.txt': b'attribution'}
        self.contract.write_text(json.dumps({'source_sha256': 'source fixture',
            'texture_hash_aliases': [
                {'native': 123, 'original': 456, 'modern': False},
                {'native': 789, 'original': 1011, 'modern': True}],
            'resources': {'a': record(self.payload['romfs/a'])},
            'notices': {'licenses/NOTICE.txt': record(self.payload['licenses/NOTICE.txt'])}}))
        from unittest.mock import patch
        patcher = patch.object(assets, 'CONTRACT', self.contract)
        patcher.start()
        self.addCleanup(patcher.stop)

    def pack(self, entries=None):
        import zipfile
        path = self.root / 'native-ui.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            for name, data in (entries or self.payload).items():
                archive.writestr(name, data)
        return path

    def test_offline_install_preserves_original_and_installs_notices(self):
        source = self.root / 'romfs'
        source.write_bytes(NativeRomFsTests().fixture())
        before = source.read_bytes()
        output = self.root / 'prepared'
        receipt = assets.prepare(source, output, resources=self.pack(), notices_directory=self.root / 'notices')
        self.assertEqual(assets.RomFs(output).read('a'), b'intended UI')
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual((self.root / 'notices/NOTICE.txt').read_bytes(), b'attribution')
        self.assertEqual(receipt['resources']['a']['bytes'], 11)
        self.assertEqual(receipt['texture_hash_aliases'], [
            {'native': 123, 'original': 456, 'modern': False},
            {'native': 789, 'original': 1011, 'modern': True}])

    def test_bad_or_incomplete_pack_never_changes_game_data(self):
        source = self.root / 'romfs'
        source.write_bytes(NativeRomFsTests().fixture())
        output = self.root / 'prepared'
        for entries in ({'romfs/a': b'intended UI'},
                        {**self.payload, 'romfs/a': b'corrupt art'},
                        {**self.payload, '../extra': b'unexpected'}):
            with self.subTest(entries=list(entries)), self.assertRaises(ValueError):
                assets.prepare(source, output, resources=self.pack(entries))
            self.assertFalse(output.exists())
            self.assertEqual(assets.RomFs(source).read('a'), b'ROM!')

    def test_duplicate_and_symlink_entries_are_rejected(self):
        import warnings
        import zipfile
        path = self.pack()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(path, 'a') as archive:
                archive.writestr('romfs/a', b'intended UI')
        with self.assertRaises(ValueError):
            assets.read_pack(path)
        path = self.pack()
        with zipfile.ZipFile(path, 'w') as archive:
            item = zipfile.ZipInfo('romfs/a')
            item.external_attr = 0o120777 << 16
            archive.writestr(item, b'intended UI')
            archive.writestr('licenses/NOTICE.txt', b'attribution')
        with self.assertRaises(ValueError):
            assets.read_pack(path)
