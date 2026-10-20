import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from retuned.rom import inspect
from retuned.settings import Settings
from retuned.textures import discover


class ServicesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def cartridge(self):
        data = bytearray(1536)
        data[0x100:0x104] = b'NCSD'
        struct.pack_into('<II', data, 0x120, 1, 2)
        data[0x300:0x304] = b'NCCH'
        struct.pack_into('<Q', data, 0x318, 0x0004000000033500)
        data[0x38f] = 4
        rom = self.root / 'synthetic.3ds'
        rom.write_bytes(data)
        catalog = self.root / 'catalog.json'
        catalog.write_text(json.dumps({'roms': [{
            'region': 'USA', 'program_id': '0004000000033500',
            'sha256': hashlib.sha256(data).hexdigest()}]}))
        return rom, catalog

    def test_verified_cartridge_read_only(self):
        rom, catalog = self.cartridge()
        before = rom.read_bytes()
        self.assertEqual(inspect(rom, catalog)['region'], 'USA')
        self.assertEqual(before, rom.read_bytes())

    def test_wrong_title_rejected_even_with_matching_hash(self):
        rom, catalog = self.cartridge()
        entries = json.loads(catalog.read_text())
        entries['roms'][0]['program_id'] = '0004000000125500'
        catalog.write_text(json.dumps(entries))
        with self.assertRaisesRegex(ValueError, 'region'):
            inspect(rom, catalog)

    def test_encrypted_cartridge_rejected(self):
        rom, catalog = self.cartridge()
        data = bytearray(rom.read_bytes())
        data[0x38f] = 0
        rom.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'Encrypted'):
            inspect(rom, catalog)

    def test_truncated_partition_rejected(self):
        rom, catalog = self.cartridge()
        rom.write_bytes(rom.read_bytes()[:-1])
        with self.assertRaisesRegex(ValueError, 'bounds'):
            inspect(rom, catalog)

    def test_modified_rom_rejected(self):
        rom, catalog = self.cartridge()
        with rom.open('r+b') as stream:
            stream.seek(1400)
            stream.write(b'changed')
        with self.assertRaisesRegex(ValueError, 'Unverified'):
            inspect(rom, catalog)

    def test_startup_and_gameplay_share_edits(self):
        startup, gameplay = Settings(self.root), Settings(self.root)
        startup.update({'bindings': {'a': 'east', 'b': 'south'}})
        self.assertEqual(gameplay.read()['bindings']['a'], 'east')
        gameplay.update({'bindings': {'item_i': 'custom'}})
        self.assertEqual(startup.read()['bindings']['item_i'], 'custom')
        self.assertEqual(startup.read()['bindings']['b'], 'south')
        self.assertEqual(startup.read()['bindings']['target'], 'left_trigger')

    def test_settings_do_not_touch_saves(self):
        save = self.root / 'user/save.bin'
        save.parent.mkdir()
        save.write_bytes(b'progress')
        Settings(self.root).update({'language': 'fr'})
        self.assertEqual(Settings(self.root).read()['language'], 'fr')
        self.assertEqual(save.read_bytes(), b'progress')

    def test_malformed_settings_preserved(self):
        path = self.root / 'settings.json'
        path.write_text('{incomplete')
        with self.assertRaises(ValueError):
            Settings(self.root).update({'language': 'en'})
        self.assertEqual(path.read_text(), '{incomplete')

    def test_textures_in_subfolders(self):
        path = self.root / 'pack/actor/link'
        path.mkdir(parents=True)
        (path / 'face.PNG').write_bytes(b'test')
        (self.root / 'pack/readme.txt').write_text('pack')
        self.assertEqual(list(discover(self.root / 'pack')), [Path('actor/link/face.PNG')])

    def test_texture_symlinks_do_not_escape_or_loop(self):
        pack = self.root / 'pack'
        pack.mkdir()
        (self.root / 'outside.png').write_bytes(b'test')
        (pack / 'external.png').symlink_to(self.root / 'outside.png')
        (pack / 'loop').symlink_to(pack, target_is_directory=True)
        self.assertEqual(list(discover(pack)), [])


if __name__ == '__main__':
    unittest.main()
