"""Privacy gates must cover Windows separators, wide strings and every DLL."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/native'))
from runtime_paths import verify_runtime_paths


class RuntimePathPrivacy(unittest.TestCase):
    def test_home_path_in_dependency_rejects_even_when_host_is_clean(self):
        with tempfile.TemporaryDirectory() as temporary:
            host = Path(temporary) / 'host.exe'
            library = Path(temporary) / 'renderer.dll'
            host.write_bytes(b'neutral host')
            for value, encoding in ((r'c:\users\Example\engine\file.cpp', 'utf-8'),
                                    ('C:/Users/Example/engine/file.cpp', 'utf-16-le'),
                                    ('C:/Users/Éxample/engine/file.cpp', 'utf-8')):
                library.write_bytes(value.encode(encoding))
                roots = ['C:/Users/Éxample' if 'É' in value else 'C:/Users/Example']
                with self.assertRaisesRegex(ValueError, 'renderer.dll'):
                    verify_runtime_paths([host, library], roots)
                self.assertEqual(library.read_bytes(), value.encode(encoding))

    def test_mapped_source_names_pass_but_empty_scan_roots_do_not(self):
        with tempfile.TemporaryDirectory() as temporary:
            binary = Path(temporary) / 'host.exe'
            binary.write_bytes(b'retuned-source/engine/file.cpp')
            verify_runtime_paths([binary], ['C:/Users/Example', '/Users/Example'])
            with self.assertRaises(ValueError):
                verify_runtime_paths([binary], [])
