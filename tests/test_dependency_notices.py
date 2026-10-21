"""A bundled dependency must retain its notice and exact distro source identity."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/native'))
spec = importlib.util.spec_from_file_location('desktop_staging', ROOT / 'tools/native/stage_desktop_host.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class DependencyNotices(unittest.TestCase):
    def test_multiarch_owner_retains_source_version_and_referenced_license(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            docs, common, notices = root / 'doc', root / 'common', root / 'notices'
            (docs / 'libexample1').mkdir(parents=True)
            common.mkdir()
            notices.mkdir()
            (docs / 'libexample1/copyright').write_text('License text: /usr/share/common-licenses/LGPL-2.1\n')
            (common / 'LGPL-2.1').write_text('complete license fixture')
            owner = subprocess.CompletedProcess([], 0, 'libexample1:amd64: /lib/libexample.so.1\n', '')
            with patch.object(stage.subprocess, 'run', return_value=owner), patch.object(stage, 'run', return_value='libexample1:amd64\t1.2-3\texample\t1:1.2-3'):
                stage.linux_dependency_notices([root / 'libexample.so.1'], notices, docs, common)
            entry = json.loads((notices / 'linux-dependency-sources.json').read_text())['dependencies'][0]
            self.assertEqual(entry['source_version'], '1:1.2-3')
            self.assertTrue(entry['source_record'].endswith('/example/1%3A1.2-3'))
            self.assertEqual((notices / 'common-licenses/LGPL-2.1').read_text(), 'complete license fixture')

    def test_unidentified_binary_cannot_silently_ship_without_a_notice(self):
        absent = subprocess.CompletedProcess([], 1, '', 'no path found')
        with tempfile.TemporaryDirectory() as temporary, patch.object(stage.subprocess, 'run', return_value=absent):
            with self.assertRaisesRegex(ValueError, 'Cannot identify dependency package'):
                stage.linux_dependency_notices([Path(temporary) / 'unknown.so'], Path(temporary))
