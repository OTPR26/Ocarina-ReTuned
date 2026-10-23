"""Run the actual save codec and transaction implementation on a local JVM."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class AndroidSaveFilesTests(unittest.TestCase):
    def test_codec_and_local_recovery(self):
        java_home = os.environ.get("JAVA_HOME")
        javac = str(Path(java_home) / "bin/javac") if java_home else shutil.which("javac")
        if not javac:
            self.skipTest("Java 17+ is needed for the Android save tests")
        java = str(Path(javac).with_name("java"))
        with tempfile.TemporaryDirectory(prefix="retuned-save-tests-") as output:
            subprocess.run([javac, "-d", output,
                str(ROOT / "tools/native/android/SaveFilesCore.java"),
                str(ROOT / "tests/android/SaveFilesCoreCheck.java")], check=True, capture_output=True)
            subprocess.run([java, "-cp", output, "org.triaevum.android.SaveFilesCoreCheck"],
                check=True, capture_output=True)

if __name__ == "__main__":
    unittest.main()
