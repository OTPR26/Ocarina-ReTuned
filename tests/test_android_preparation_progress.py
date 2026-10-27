"""Check preparation milestones and time estimates on a local JVM."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class AndroidPreparationProgressTests(unittest.TestCase):
    def test_progress_and_estimates(self):
        java_home = os.environ.get("JAVA_HOME")
        javac = str(Path(java_home) / "bin/javac") if java_home else shutil.which("javac")
        if not javac:
            self.skipTest("Java 17+ is needed for the Android preparation tests")
        java = str(Path(javac).with_name("java"))
        with tempfile.TemporaryDirectory(prefix="retuned-progress-tests-") as output:
            subprocess.run([javac, "-d", output,
                str(ROOT / "tools/native/android/PreparationProgress.java"),
                str(ROOT / "tests/android/PreparationProgressCheck.java")], check=True, capture_output=True)
            subprocess.run([java, "-cp", output, "org.triaevum.android.PreparationProgressCheck"],
                check=True, capture_output=True)

if __name__ == "__main__":
    unittest.main()
