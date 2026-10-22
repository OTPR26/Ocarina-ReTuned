import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import tarfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('release_assets', Path(__file__).parents[1] / 'tools/native/audit_release_assets.py')
release_assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_assets)


class ReleaseAssetAuditTests(unittest.TestCase):
    def test_linux_tar_cannot_hide_private_payload_or_archive_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = b'private fixture in Linux package'
            contract = root / 'contract.json'
            contract.write_text(json.dumps({'resources': {'ui': {'sha256': hashlib.sha256(payload).hexdigest()}}}))
            package = root / 'preview.tar.gz'
            with tarfile.open(package, 'w:gz') as archive:
                entry = tarfile.TarInfo('resources/renamed.bin')
                entry.size = len(payload)
                archive.addfile(entry, io.BytesIO(payload))
            self.assertEqual(release_assets.audit([package], contract)['status'], 'FAIL')
            with tarfile.open(package, 'w:gz') as archive:
                entry = tarfile.TarInfo('outside')
                entry.type = tarfile.SYMTYPE
                entry.linkname = '../../private'
                archive.addfile(entry)
            with self.assertRaisesRegex(ValueError, 'Unsafe, linked'):
                release_assets.audit([package], contract)

    def test_private_resource_is_rejected_even_when_renamed_and_nested(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = b'private UI fixture'
            contract = root / 'contract.json'
            contract.write_text(json.dumps({'resources': {'message/eu/eu.qm': {'sha256': hashlib.sha256(payload).hexdigest()}}}))
            inner = io.BytesIO()
            with zipfile.ZipFile(inner, 'w') as archive:
                archive.writestr('renamed.bin', payload)
            package = root / 'preview.zip'
            with zipfile.ZipFile(package, 'w') as archive:
                archive.writestr('setup/resources.zip', inner.getvalue())
                archive.writestr('resources/own-font.qbf', b'original font artwork')
            result = release_assets.audit([package], contract)
            self.assertEqual(result['status'], 'FAIL')
            self.assertEqual(len(result['findings']), 1)
            self.assertEqual(result['findings'][0]['resource'], 'message/eu/eu.qm')
            with zipfile.ZipFile(package, 'w') as archive:
                archive.writestr('resources/own-font.qbf', b'original font artwork')
            self.assertEqual(release_assets.audit([package], contract)['status'], 'PASS')
