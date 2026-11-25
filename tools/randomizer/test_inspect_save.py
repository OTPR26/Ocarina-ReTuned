import hashlib
import struct
import tempfile
import unittest
from pathlib import Path

from inspect_save import inspect


class InspectSaveTest(unittest.TestCase):
    def test_reward_fields_and_pair_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            identity = ('retuned-randomizer-save-v1\n' + 'a'*64 + '\n'
                        + 'b'*64 + '\n1244\n').encode()
            (root / 'identity').write_bytes(identity)
            (root / 'native').mkdir()
            native = bytearray(0x14dc)
            native[0x30:0x36] = b'ZELDAZ'
            struct.pack_into('<H', native, 0x42, 64)
            struct.pack_into('<I', native, 0xec + 40*28, 5)
            native[0x4e] = 1
            extended = bytearray(1244)
            struct.pack_into('<I', extended, 0, 19)
            (root / 'native/save00.bin').write_bytes(native)
            path = root / ('slot0-' + hashlib.sha256(native).hexdigest() + '.state')
            payload = identity + native + extended
            record = payload + hashlib.sha256(payload).hexdigest().encode()
            path.write_bytes(record)
            result = inspect(root, 0)
            self.assertEqual(result['health_capacity'], 64)
            self.assertEqual(result['magic_acquired'], 1)
            self.assertEqual(result['opened_chests'], {'40': 5})
            self.assertEqual(result['extended_version'], 19)
            changed = bytearray(record)
            changed[-70] ^= 1
            path.write_bytes(changed)
            with self.assertRaises(ValueError):
                inspect(root, 0)
            path.write_bytes(record[:-1])
            with self.assertRaises(ValueError):
                inspect(root, 0)
            with self.assertRaises(ValueError):
                inspect(root, 3)


if __name__ == '__main__':
    unittest.main()
