import importlib.util
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('reframed_image', Path(__file__).parents[1] / 'tools/reframed/prepare_native_image.py')
image = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image)


class ReframedImageTests(unittest.TestCase):
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
        with patch.object(image.subprocess, 'check_output', return_value=listing):
            symbols = image.elf_symbols(Path('readelf'), Path('mod.elf'))
        self.assertEqual([s[3] for s in symbols], ['__atomic_helper', 'svc_wrapper', '__text_end'])


if __name__ == '__main__':
    unittest.main()
