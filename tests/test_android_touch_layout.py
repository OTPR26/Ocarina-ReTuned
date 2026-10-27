"""Layout persistence and invalid-input checks without requiring a device."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]

class AndroidTouchLayoutTests(unittest.TestCase):
    def test_layout_roundtrip(self):
        java_home = os.environ.get('JAVA_HOME')
        javac = str(Path(java_home) / 'bin/javac') if java_home else shutil.which('javac')
        if not javac or subprocess.run([javac, '-version'], capture_output=True).returncode:
            self.skipTest('Set JAVA_HOME to an installed JDK')
        with tempfile.TemporaryDirectory(prefix='retuned-touch-layout-') as output:
            subprocess.run([javac, '-d', output,
                str(ROOT / 'tools/native/android/TouchLayout.java'),
                str(ROOT / 'tests/android/TouchLayoutCheck.java')], check=True, capture_output=True)
            subprocess.run([str(Path(javac).with_name('java')), '-cp', output,
                'org.triaevum.android.TouchLayoutCheck'], check=True, capture_output=True)

    def test_reapplying_native_input_does_not_duplicate_touch_sampling(self):
        sys.path[:0]=[str(ROOT/'tools/frontend'),str(ROOT/'tools/reframed')]
        from apply_mobile_frontend import stage_touch_input
        template=(ROOT/'tools/frontend/touch_input.cpp.inc').read_text()
        anchor='  auto frame = MapNativeControlInput(config, host, aimTransform,'
        legacy=template.replace('{T::Map,NativeControlAction::Zl},','')
        with tempfile.TemporaryDirectory() as output:
            path=Path(output)/'input.cpp'
            path.write_text('// Keep owner changes\n'+legacy+'\n'+anchor+'args);\n')
            stage_touch_input(path,template)
            first=path.read_text()
            stage_touch_input(path,template)
            self.assertEqual(path.read_text(),first)
            self.assertEqual(first.count('SampleTouch(guestRefreshWillConsume)'),1)
            self.assertEqual(first.count('{T::Map,NativeControlAction::Zl}'),1)
            self.assertTrue(first.startswith('// Keep owner changes\n'))
