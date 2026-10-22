import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location('ui_texture', Path(__file__).resolve().parents[1] / 'tools/native/ui_texture.py')
texture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(texture)


class LocalTextureTests(unittest.TestCase):
    def template(self):
        data = bytearray(72 + 128)
        data[:4] = b'ctxb'
        struct.pack_into('<II', data, 4, len(data), 1)
        struct.pack_into('<II', data, 16, 24, 72)
        data[24:28] = b'tex '
        struct.pack_into('<II', data, 28, 48, 1)
        struct.pack_into('<IHHHHHHI', data, 36, 128, 1, 0, 8, 8, 0x6752, 0x8033, 0)
        return bytes(data)

    def test_channel_order_matches_native_decoder_and_tile_boundaries(self):
        rgba = bytes((x % 16 * 17, y % 16 * 17, 85, 255) [c]
                     for y in range(16) for x in range(24) for c in range(4))
        encoded = texture.encode(self.template(), 24, 16, rgba)
        self.assertEqual(texture.decode(encoded), (24, 16, rgba))
        self.assertEqual(struct.unpack_from('<H', encoded, 72)[0], 0x005f)

    def test_reject_truncation_mips_and_wrong_buffer(self):
        original = self.template()
        for broken in (original[:-1], original + b'x'):
            with self.assertRaises(ValueError): texture.decode(broken)
        broken = bytearray(original)
        struct.pack_into('<H', broken, 40, 2)
        with self.assertRaises(ValueError): texture.decode(broken)
        with self.assertRaises(ValueError): texture.encode(original, 8, 8, b'wrong')
        with self.assertRaises(ValueError): texture.encode(original, 4096, 4096, b'')

    def test_etc1_alpha_column_order_and_truncation(self):
        data = bytearray(self.template()[:72])
        # Four ETC1 blocks form an 8x8 tile. Individual color mode and table0
        # with index0 produce RGB(2,2,2); alpha ramps by column, then row.
        alpha = sum(i << (i * 4) for i in range(16))
        raw = struct.pack('<QQ', alpha, 0) * 4
        data += raw
        struct.pack_into('<I', data, 4, len(data))
        struct.pack_into('<IHHHHHHI', data, 36, len(raw), 1, 1, 8, 8, 0x675b, 0, 0)
        w, h, rgba = texture.decode_compressed(data)
        self.assertEqual((w, h), (8, 8))
        for y in range(8):
            for x in range(8):
                at = (y * 8 + x) * 4
                self.assertEqual(rgba[at:at+4], bytes((2, 2, 2, ((x % 4) * 4 + y % 4) * 17)))
        with self.assertRaises(ValueError): texture.decode_compressed(data[:-1])
