"""Hosted artifacts must never contain game data, credentials, or build paths."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('host_archive', ROOT / 'tools/ci/archive_host_components.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class HostComponents(unittest.TestCase):
    def test_private_files_and_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, data in [('save.sav', b'data'), ('key.p12', b'data'),
                               ('PrivateGame/code.bin', b'data'),
                               ('runtime', b'path=/Users/example/project')]:
                with self.subTest(name=name):
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                    with self.assertRaises(ValueError):
                        module.check_file(path, root)

    def test_symlink_cannot_escape_artifact_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'runtime').symlink_to('/etc/hosts')
            with self.assertRaises(ValueError):
                module.check_file(root / 'runtime', root)

    def test_neutral_component_has_verifiable_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'runtime').write_bytes(b'neutral runtime')
            record = module.check_file(root / 'runtime', root)
            self.assertEqual(record['bytes'], 15)
            self.assertEqual(len(record['sha256']), 64)


if __name__ == '__main__':
    unittest.main()
