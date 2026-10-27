"""Exercise local tvOS save recovery using an isolated preferences domain."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(sys.platform == "darwin", "Apple Foundation frameworks required")
class TVSaveBackupTests(unittest.TestCase):
    def test_cache_eviction_and_existing_save_preservation(self):
        compiler = shutil.which("clang++")
        if not compiler:
            self.skipTest("Clang required")
        with tempfile.TemporaryDirectory(prefix="retuned-tv-save-tests-") as folder:
            for name in ("tvos_save_backup", "save_sync_files", "apple/data_paths"):
                binary = Path(folder) / Path(name).name
                subprocess.run([
                    compiler, "-std=c++20", "-fobjc-arc", str(ROOT / "tests" / (name + ".mm")),
                    "-framework", "Foundation", "-framework", "CloudKit", "-framework", "Security",
                    "-o", str(binary),
                ], check=True, capture_output=True)
                subprocess.run([str(binary)], check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
