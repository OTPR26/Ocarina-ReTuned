from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/native'))
from audit_frontend_settings import verify


class FrontendSettingsAuditTests(unittest.TestCase):
    def test_missing_platform_controls_fail_for_a_dual_capable_host(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'host'
            path.write_bytes(b'Java_org_triaevum_android_RetunedDualScreen_surface\0')
            with self.assertRaisesRegex(ValueError, 'Screen mode'):
                verify(path)
            path.write_bytes(path.read_bytes() + b'Screen mode\0Bottom equipment panel\0')
            self.assertEqual(verify(path)['display_controls'], 'PASS')

    def test_release_contract_can_require_dual_controls_even_if_backend_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'host'
            path.write_bytes(b'ordinary desktop host')
            verify(path)
            with self.assertRaises(ValueError):
                verify(path, require_dual=True)
