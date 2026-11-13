import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('linux_compiler_sources',
    Path(__file__).resolve().parents[1] / 'tools/native/audit_linux_compiler_sources.py')
sources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sources)


class CompilerSources(unittest.TestCase):
    def fixture(self, root):
        archive = root / 'compiler.orig.tar.xz'
        archive.write_bytes(b'source fixture')
        checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
        (root / 'compiler.dsc').write_text('-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA512\n\n'
            'Source: compiler\nVersion: 13.3\nChecksums-Sha256:\n'
            f' {checksum} {archive.stat().st_size} {archive.name}\n'
            '-----BEGIN PGP SIGNATURE-----\n')
        manifest = root / 'manifest.json'
        manifest.write_text(json.dumps({'packages': [
            {'source': 'compiler (13.3)', 'version': '13.3+b1'}]}))
        return manifest

    def test_exact_source_and_checksums(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.fixture(root)
            result = sources.audit(root, [manifest])
            self.assertEqual(result['sources'][0]['version'], '13.3')
            self.assertIn('compiler.orig.tar.xz', result['sources'][0]['files'])
            (root / 'compiler.orig.tar.xz').write_bytes(b'changed fixture')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                sources.audit(root, [manifest])

    def test_other_source_version_does_not_satisfy_binary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.fixture(root)
            manifest.write_text(json.dumps({'packages': [{'source': 'compiler', 'version': '13.4'}]}))
            with self.assertRaisesRegex(ValueError, 'Missing matching source'):
                sources.audit(root, [manifest])
