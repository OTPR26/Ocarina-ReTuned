"""Reject mixed-architecture packages using binary headers, not file names."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/native'))
spec = importlib.util.spec_from_file_location('desktop_host',
    Path(__file__).resolve().parents[1] / 'tools/native/stage_desktop_host.py')
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)


class DesktopArchitecture(unittest.TestCase):
    def test_elf_machine_is_used_even_with_misleading_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'Linux-x86_64'
            for machine, expected in ((62, 'x86_64'), (183, 'arm64')):
                header = bytearray(64)
                header[:6] = b'\x7fELF\x02\x01'
                header[18:20] = machine.to_bytes(2, 'little')
                path.write_bytes(header)
                self.assertEqual(host.binary_architecture(path, 'linux'), expected)
            path.write_bytes(b'not an ELF library')
            with self.assertRaises(ValueError):
                host.binary_architecture(path, 'linux')

    def test_pe_rejects_32_bit_arm_and_x86(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'library.dll'
            for machine, expected in ((0x8664, 'x86_64'), (0xAA64, 'arm64'),
                                      (0x14c, None), (0x1c4, None)):
                header = bytearray(134)
                header[:2] = b'MZ'
                header[60:64] = (128).to_bytes(4, 'little')
                header[128:132] = b'PE\0\0'
                header[132:134] = machine.to_bytes(2, 'little')
                path.write_bytes(header)
                if expected:
                    self.assertEqual(host.binary_architecture(path, 'windows'), expected)
                else:
                    with self.assertRaises(ValueError):
                        host.binary_architecture(path, 'windows')
