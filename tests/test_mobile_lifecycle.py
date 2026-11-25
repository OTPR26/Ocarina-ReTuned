from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class MobileLifecycleTests(unittest.TestCase):
    def test_pause_resume_and_missed_will_background(self):
        compiler = shutil.which('clang++') or shutil.which('c++')
        if not compiler:
            self.skipTest('Requires a C++20 compiler')
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'lifecycle'
            subprocess.run([compiler, '-std=c++20', '-I'+str(ROOT/'tests/lifecycle_stub'),
                str(ROOT/'tests/mobile_lifecycle.cpp'), '-o', str(output)],check=True,capture_output=True)
            subprocess.run([str(output)],check=True,capture_output=True)
