"""A newer build SDK must not hide a bundled library's higher minimum OS."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/native'))
import macos_deployment as deployment


class MacDeployment(unittest.TestCase):
    def test_runtime_minimum_is_independent_of_sdk(self):
        text = 'platform MACOS\n minos 13.4\n sdk 27.0\n'
        self.assertEqual(deployment.parse_minimum(text), '13.4')
        with self.assertRaises(ValueError):
            deployment.parse_minimum('platform IOS\n minos 13.4\n sdk 27.0\n')

    def test_dependency_with_higher_minimum_rejects_package_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            contents = Path(temporary)
            runtime = contents / 'runtime'
            runtime.write_bytes(b'\xcf\xfa\xed\xfeunchanged binary fixture')
            with patch.object(deployment.subprocess, 'check_output',
                              return_value='platform MACOS\n minos 27.0\n sdk 27.0\n'):
                with self.assertRaisesRegex(ValueError, 'above package target 13.4'):
                    deployment.check_bundle(contents, '13.4')
                self.assertEqual(deployment.check_bundle(contents, '27.0')['binaries'][0]['minimum_macos'], '27.0')
            self.assertEqual(runtime.read_bytes(), b'\xcf\xfa\xed\xfeunchanged binary fixture')

    def test_version_comparison_is_numeric_and_requires_known_format(self):
        self.assertGreater(deployment.version_tuple('13.10'), deployment.version_tuple('13.4'))
        self.assertEqual(deployment.version_tuple('13.4'), deployment.version_tuple('13.4.0'))
        with self.assertRaises(ValueError):
            deployment.version_tuple('current')
