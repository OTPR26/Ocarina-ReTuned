import importlib.util
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('reframed_image', Path(__file__).parents[1] / 'tools/reframed/prepare_native_image.py')
image = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image)


class ReframedImageTests(unittest.TestCase):
    def test_file_selection_spacing_is_bounded_and_idempotent(self):
        code = bytearray(48)
        struct.pack_into('<IIII', code, 0, 0xE3E01007, 0, 0, 0)
        struct.pack_into('<IIII', code, 16, 0xE3A01002, 0, 0xE3A01002, 0)
        struct.pack_into('<I', code, 32, 0xE3A01002)  # unrelated viewport
        named = {'SingleScreen_BeforeFileScene': (image.BASE, 16, 'FUNC', 1),
                 'SingleScreen_DrawFileText': (image.BASE + 16, 8, 'FUNC', 1),
                 'SingleScreen_BeforeFileBackdrop': (image.BASE + 24, 8, 'FUNC', 1)}
        image.apply_file_selection_spacing(code, named)
        self.assertEqual(struct.unpack_from('<I', code, 0)[0], 0xE3E0100F)
        self.assertEqual(struct.unpack_from('<I', code, 16)[0], 0xE3E01005)
        self.assertEqual(struct.unpack_from('<I', code, 24)[0], 0xE3E01005)
        self.assertEqual(struct.unpack_from('<I', code, 32)[0], 0xE3A01002)
        result = bytes(code)
        image.apply_file_selection_spacing(code, named)
        self.assertEqual(bytes(code), result)
        struct.pack_into('<I', code, 24, 0)
        with self.assertRaises(ValueError):
            image.apply_file_selection_spacing(code, named)
        self.assertEqual(struct.unpack_from('<I', code, 0)[0], 0xE3E0100F)

    def test_touch_action_owner_requires_matching_adapter(self):
        code=bytearray(128)
        struct.pack_into('<II',code,8,0xE59F3030,0xE5933000)
        struct.pack_into('<I',code,64,0x12345678)
        self.assertEqual(image.touch_action_owner(code,image.BASE),0x12345678)
        struct.pack_into('<I',code,12,0xE5933004)
        with self.assertRaises(ValueError):
            image.touch_action_owner(code,image.BASE)

    def test_literal_and_rle_records(self):
        payload = b'PATCH' + b'\x00\x00\x02\x00\x02AB' + b'\x00\x00\x06\x00\x00\x00\x03ZEOF'
        result, intervals = image.apply_ips(bytes(5), payload)
        self.assertEqual(result, b'\0\0AB\0\0ZZZ')
        self.assertEqual(intervals, [(image.BASE + 2, 2), (image.BASE + 6, 3)])

    def test_malformed_patches_fail(self):
        for payload in (b'', b'PATCH', b'PATCH\0\0\0\0\x02A', b'PATCHEOFextra', b'PATCH\xff\xff\xff\0\x01xEOF'):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                image.apply_ips(b'', payload)

    def test_adjusted_hook_return_is_registered(self):
        code = bytearray(0x200)
        hook = image.BASE + 0x100
        # BL hook; the conditional ADD LR, LR, #12 skips three instructions.
        struct.pack_into('<I', code, 0, 0xEB000000 | ((hook-image.BASE-8)//4))
        struct.pack_into('<I', code, 0x100, 0x028EE00C)
        functions = [{'name': 'hook_Menu', 'entry': hook, 'size': 4}]
        self.assertEqual(image.adjusted_return_sites(code, [(image.BASE,4)], functions), [image.BASE+16])
        # A matching word in an unpatched interval must not create a resume point.
        self.assertEqual(image.adjusted_return_sites(code, [], functions), [])
        struct.pack_into('<I', code, 0x100, 0x024EE004)
        self.assertEqual(image.adjusted_return_sites(code, [(image.BASE,4)], functions), [image.BASE])

    def test_elf_mapping_separates_instructions_and_data(self):
        listing = '''
  1: 005c7000 0 NOTYPE LOCAL DEFAULT 67 $a
  2: 005c7000 12 FUNC LOCAL DEFAULT 67 __atomic_helper
  3: 005c700c 0 NOTYPE LOCAL DEFAULT 67 $d
  4: 005c700c 4 NOTYPE LOCAL DEFAULT 67 constant_table
  5: 005c7010 0 NOTYPE LOCAL DEFAULT 67 $a
  6: 005c7010 0 FUNC GLOBAL DEFAULT 67 svc_wrapper
  7: 005c701c 0 NOTYPE GLOBAL DEFAULT 67 __text_end
'''
        rows = [line.split() for line in listing.splitlines() if line.strip()]
        names = b'\0'
        symbols = bytearray()
        for row in rows:
            address, length, kind, label = int(row[1], 16), int(row[2]), row[3], row[-1]
            name = len(names)
            names += label.encode() + b'\0'
            symbols.extend(struct.pack('<IIIBBH', name, address, length, 2 if kind == 'FUNC' else 0, 0, 1))
        elf = bytearray(52 + 4 * 40)
        elf[:7] = b'\x7fELF\x01\x01\x01'
        struct.pack_into('<H', elf, 18, 40)
        struct.pack_into('<I', elf, 32, 52)
        struct.pack_into('<HH', elf, 46, 40, 4)
        struct.pack_into('<10I', elf, 52 + 2 * 40, 0, 3, 0, 0, len(elf), len(names), 0, 0, 1, 0)
        struct.pack_into('<10I', elf, 52 + 3 * 40, 0, 2, 0, 0, len(elf) + len(names), len(symbols), 2, 0, 4, 16)
        elf.extend(names)
        elf.extend(symbols)
        with patch.object(Path, 'read_bytes', return_value=bytes(elf)):
            symbols = image.elf_symbols(None, Path('mod.elf'))
        self.assertEqual([s[3] for s in symbols], ['__atomic_helper', 'svc_wrapper', '__text_end'])

    def test_elf_rejects_truncated_or_wrong_machine(self):
        for payload in (b'', b'\x7fELF' + bytes(48), b'\x7fELF\x01\x01\x01' + bytes(45)):
            with patch.object(Path, 'read_bytes', return_value=payload), self.assertRaises(ValueError):
                image.read_elf_symbols(Path('bad.elf'))


if __name__ == '__main__':
    unittest.main()
