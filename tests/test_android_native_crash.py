"""Exercise native crash decoding and its privacy boundary without an Android device."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AndroidNativeCrashTests(unittest.TestCase):
    def test_frames_and_private_fields(self):
        java_home = os.environ.get('JAVA_HOME')
        javac = str(Path(java_home) / 'bin/javac') if java_home else shutil.which('javac')
        if not javac:
            self.skipTest('Java is required')
        if subprocess.run([javac, '-version'], capture_output=True).returncode:
            self.skipTest('Set JAVA_HOME to an installed JDK')
        with tempfile.TemporaryDirectory(prefix='retuned-native-report-') as output:
            subprocess.run([javac, '-d', output,
                str(ROOT / 'tools/native/android/NativeCrashReport.java'),
                str(ROOT / 'tests/android/NativeCrashReportCheck.java')], check=True, capture_output=True)
            subprocess.run([str(Path(javac).with_name('java')), '-cp', output,
                'org.triaevum.android.NativeCrashReportCheck'], check=True, capture_output=True)
