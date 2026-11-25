from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import sys

ROOT=Path(__file__).resolve().parents[1]
@unittest.skipUnless(sys.platform=='darwin','Requires Foundation')
class BackgroundFailureTests(unittest.TestCase):
    def test_only_background_denial_skips_settings_reset(self):
        with tempfile.TemporaryDirectory() as folder:
            binary=Path(folder)/'background-failure'
            subprocess.run([shutil.which('clang++'),'-std=c++20','-fobjc-arc',
                str(ROOT/'tests/background_failure.mm'),'-framework','Foundation','-o',str(binary)],check=True,capture_output=True)
            subprocess.run([str(binary)],check=True,capture_output=True)
