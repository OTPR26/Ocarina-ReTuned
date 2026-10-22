import importlib.util
import base64
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('identity_audit', Path(__file__).parents[1] / 'tools/native/audit_release_identity.py')
identity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(identity)


class ReleaseIdentityTests(unittest.TestCase):
    def test_pem_parser_strings_are_not_key_material(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'library.bin'
            path.write_bytes(b'-----BEGIN PRIVATE KEY-----\0parser\0-----END PRIVATE KEY-----')
            self.assertEqual(identity.audit([path], [])['status'], 'PASS')
            path.write_bytes(b'-----BEGIN PRIVATE KEY-----\n' +
                             base64.b64encode(b'\x30' + b'x' * 80) +
                             b'\n-----END PRIVATE KEY-----')
            self.assertEqual(identity.audit([path], [])['status'], 'FAIL')

    def test_nested_profile_and_utf16_identity_are_reported_without_the_value(self):
        with tempfile.TemporaryDirectory() as directory:
            inner = io.BytesIO()
            with zipfile.ZipFile(inner, 'w') as archive:
                archive.writestr('Payload/Test.app/embedded.mobileprovision', b'profile')
                archive.writestr('Payload/Test.app/program', 'Private Example'.encode('utf-16le'))
            path = Path(directory) / 'package.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('nested.ipa', inner.getvalue())
            report = identity.audit([path], [{'label': 'owner_name', 'value': 'Private Example'}])
            self.assertEqual(report['status'], 'FAIL')
            self.assertTrue(any(r['path'].endswith('/program') and
                                r.get('marker_labels') == ['owner_name']
                                for r in report['findings']))
            self.assertTrue(any(r['issue'] == 'signing profile or key material'
                                for r in report['findings']))
            self.assertNotIn('Private Example', str(report))

    def test_pseudonymous_app_id_passes_but_personal_email_in_filename_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'package.zip'
            markers = [{'label': 'owner_email', 'value': 'person@example.test'}]
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('manifest.txt', 'io.github.otpr26.ocarinaretuned')
            self.assertEqual(identity.audit([path], markers)['status'], 'PASS')
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('person@example.test.txt', 'metadata')
            report = identity.audit([path], markers)
            self.assertEqual(report['status'], 'FAIL')
            self.assertNotIn('person@example.test', str(report))
