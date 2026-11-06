"""Exercise valid Vulkan enumeration changes without requiring a GPU."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class VulkanEnumerationTests(unittest.TestCase):
    def test_driver_list_changes_and_errors(self):
        compiler = shutil.which('c++')
        if not compiler:
            self.skipTest('C++ compiler required')
        with tempfile.TemporaryDirectory(prefix='retuned-vulkan-enumeration-') as temporary:
            executable = Path(temporary) / 'enumeration-test'
            subprocess.run([compiler, '-std=c++20', '-I', str(ROOT / 'tools/native'),
                str(ROOT / 'tests/vulkan_enumeration.cpp'), '-o', str(executable)], check=True, capture_output=True)
            subprocess.run([str(executable)], check=True, capture_output=True)
