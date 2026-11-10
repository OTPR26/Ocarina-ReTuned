from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CheatsTests(unittest.TestCase):
    def test_resource_limits_and_gameplay_guards(self):
        compiler = shutil.which('clang++') or shutil.which('c++')
        if not compiler:
            self.skipTest('Requires C++20')
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / 'cheats'
            subprocess.run([compiler, '-std=c++20', '-Wall', '-Wextra',
                            str(ROOT / 'tests/cheats.cpp'), '-o', str(executable)], check=True)
            subprocess.run([str(executable)], check=True)
