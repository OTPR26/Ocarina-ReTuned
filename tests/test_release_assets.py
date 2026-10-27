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
    def test_android_stale_tools_manifest_fails_release_audit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract = root / 'contract.json'
            contract.write_text('{"resources":{}}')
            tools = io.BytesIO()
            with zipfile.ZipFile(tools, 'w') as archive:
                archive.writestr('tool.py', b'original')
            metadata = {'format': 'retuned_preparation_asset_v1',
                        'sha256': hashlib.sha256(tools.getvalue()).hexdigest(), 'unpacked_bytes': 8}
            with zipfile.ZipFile(tools, 'a') as archive:
                archive.writestr('update.py', b'new tools')
            package = root / 'preview.apk'
            def write_manifest(value):
                with zipfile.ZipFile(package, 'w') as archive:
                    archive.writestr('assets/retuned/preparation-kit.json', json.dumps(value))
                    archive.writestr('assets/retuned/preparation-kit.zip', tools.getvalue())
            write_manifest(metadata)
            result = release_assets.audit([package], contract)
            self.assertEqual(result['status'], 'FAIL')
            self.assertEqual({item['issue'] for item in result['findings']},
                             {'preparation archive checksum mismatch', 'preparation archive size mismatch'})
            metadata.update(sha256=hashlib.sha256(tools.getvalue()).hexdigest(), unpacked_bytes=17)
            write_manifest(metadata)
            self.assertEqual(release_assets.audit([package], contract)['status'], 'PASS')

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
