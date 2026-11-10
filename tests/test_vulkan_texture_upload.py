import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class TextureUploadTests(unittest.TestCase):
    def test_burst_lifetime_alignment_and_allocation_failure(self):
        compiler = shutil.which('clang++') or shutil.which('g++')
        if not compiler:
            self.skipTest('C++ compiler unavailable')
        with tempfile.TemporaryDirectory() as temp:
            binary = pathlib.Path(temp) / 'upload-test'
            subprocess.run([compiler, '-std=c++20', '-Wall', '-Wextra', '-Werror',
                            str(ROOT / 'tests/vulkan_texture_upload.cpp'), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)
