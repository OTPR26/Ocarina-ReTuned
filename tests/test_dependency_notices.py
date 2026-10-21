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
from runtime_notices import DONOR_NOTICES, copy_runtime_donor_notices


class DependencyNotices(unittest.TestCase):
    def test_missing_source_donor_notice_prevents_partial_notice_staging(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            notices = root / 'notices'
            notices.mkdir()
            (notices / 'keep.txt').write_bytes(b'existing package notice')
            originals = {}
            for index, relative in enumerate(DONOR_NOTICES.values()):
                source = root / 'engine' / relative
                source.parent.mkdir(parents=True, exist_ok=True)
                originals[source] = ('Original copyright and permissions\r\n' + str(index)).encode()
                source.write_bytes(originals[source])
            missing = next(reversed(originals))
            missing.unlink()
            with self.assertRaisesRegex(ValueError, 'Missing original runtime donor notice'):
                copy_runtime_donor_notices(root / 'engine', notices)
            self.assertEqual(list(notices.iterdir()), [notices / 'keep.txt'])
            missing.write_bytes(originals[missing])
            copy_runtime_donor_notices(root / 'engine', notices)
            manifest = json.loads((notices / 'source-donor-notices.json').read_text())
            for record in manifest['notices']:
                self.assertEqual((notices / record['notice']).read_bytes(),
                                 originals[root / 'engine' / record['engine_source']])

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

    def test_static_windows_dependency_rejects_a_mismatched_recipe(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'installed/vcpkg').mkdir(parents=True)
            (root / 'installed/vcpkg/status').write_text('Package: example\nVersion: 1.2\nArchitecture: x64-windows-static\n')
            port = root / 'ports/example'
            port.mkdir(parents=True)
            (port / 'vcpkg.json').write_text(json.dumps({'name': 'example', 'version': '1.3'}))
            notice = root / 'installed/x64-windows-static/share/example/copyright'
            notice.parent.mkdir(parents=True)
            notice.write_text('complete original notice')
            with patch.object(stage, 'run', return_value='a' * 40):
                with self.assertRaisesRegex(ValueError, 'different versioned port'):
                    stage.windows_dependency_notices(root, root / 'notices')
                (port / 'vcpkg.json').write_text(json.dumps({'name': 'example', 'version': '1.2'}))
                stage.windows_dependency_notices(root, root / 'notices')
            result = json.loads((root / 'notices/windows-dependency-sources.json').read_text())
            self.assertEqual(result['dependencies'][0]['version'], '1.2')
            self.assertEqual((root / 'notices/vcpkg/example/copyright').read_text(), 'complete original notice')
