import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/native'))
import prepare_lower_equipment_art as art
import prepare_ui_assets
import ui_texture


def pixels(path):
    data = path.read_bytes()
    width, height = struct.unpack_from('>II', data, 16)
    compressed = b''
    at = 8
    while at < len(data):
        size = struct.unpack_from('>I', data, at)[0]
        if data[at + 4:at + 8] == b'IDAT':
            compressed += data[at + 8:at + 8 + size]
        at += size + 12
    rows = zlib.decompress(compressed)
    return width, height, b''.join(rows[y * (width * 4 + 1) + 1:(y + 1) * (width * 4 + 1)]
                                  for y in range(height))


class EquipmentArtworkTests(unittest.TestCase):
    def test_existing_installation_gets_save_art_without_game_preparation(self):
        spec=importlib.util.spec_from_file_location('lower_art_entry',ROOT/'tools/native/android/retuned_lower_art_entry.py')
        entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
        class FixtureRom:
            def __init__(self,path):self.path=path
            def read(self,name):return b'option-atlas'
        with tempfile.TemporaryDirectory() as td, patch.object(prepare_ui_assets,'RomFs',FixtureRom), patch.object(ui_texture,'decode',lambda data:(256,256,bytes([45,90,180,255])*256*256)):
            root=Path(td);(root/'saved-game.bin').write_bytes(b'preserve')
            target=Path(entry.ensure_save(td,td))
            self.assertEqual(pixels(target)[:2],(120,48))
            self.assertEqual((root/'saved-game.bin').read_bytes(),b'preserve')
            with patch.object(prepare_ui_assets,'RomFs',side_effect=AssertionError('Must reuse cached artwork')):
                self.assertEqual(entry.ensure_save(td,td),str(target))

    def test_rom_art_is_cropped_and_stone_rotated_without_pillow(self):
        atlases = {size: bytes(channel for y in range(size) for x in range(size)
                               for channel in (x % 256, y % 256, 90, 255))
                   for size in (256, 512)}
        class FixtureRom:
            def __init__(self, _): pass
            def read(self, name):
                return b'menu' if 'menu_item_parts00' in name or 'menu_option_parts00' in name else b'icons'
        def decode(data):
            size = 256 if data == b'menu' else 512
            return size, size, atlases[size]
        with tempfile.TemporaryDirectory() as td, patch.object(prepare_ui_assets, 'RomFs', FixtureRom), patch.object(ui_texture, 'decode', decode):
            out = Path(td)
            receipt = art.prepare_romfs('fixture', out)
            self.assertEqual(len(receipt['files']), 10)
            self.assertEqual(pixels(out/'save.png')[:2],(120,48))
            self.assertTrue(receipt['private_local_artifact'])
            width, height, rgba = pixels(out / 'stone.png')
            self.assertEqual((width, height), (236, 56))
            self.assertEqual(rgba[:4], bytes((253, 2, 90, 255)))
            self.assertEqual(rgba[-4:], bytes((198, 237, 90, 255)))
            width, height, rgba = pixels(out / 'boots-1.png')
            self.assertEqual((width, height), (42, 42))
            self.assertEqual(rgba[:4], bytes((80, 210, 90, 255)))
