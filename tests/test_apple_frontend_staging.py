from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AppleFrontendStagingTests(unittest.TestCase):
    def test_staged_finalizer_rejects_missing_ios_controls_before_changing_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for source in ('tools/native/apple/finalize_bundle.py',
                           'tools/native/audit_frontend_settings.py'):
                shutil.copy2(ROOT / source, root / Path(source).name)
            app = root / 'Game.app'
            app.mkdir()
            info = app / 'Info.plist'
            original = plistlib.dumps({'CFBundleExecutable': 'Game'})
            info.write_bytes(original)
            (app / 'Game').write_bytes(b'host without controls')
            icons = root / 'icons.plist'
            icons.write_bytes(plistlib.dumps({}))
            command = [sys.executable, str(root / 'finalize_bundle.py'),
                       str(app), 'ios', str(icons)]
            rejected = subprocess.run(command, cwd=root, capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(b'Compiled display settings missing', rejected.stderr)
            self.assertEqual(info.read_bytes(), original)
            (app / 'Game').write_bytes(b'Screen mode\0Bottom equipment panel\0')
            subprocess.run(command, cwd=root, check=True, capture_output=True)
            self.assertEqual(plistlib.loads(info.read_bytes())['CFBundleDisplayName'],
                             'Ocarina ReTuned')
