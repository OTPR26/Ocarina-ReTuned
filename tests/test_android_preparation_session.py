from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'Java compiler required')
class PreparationSessionTests(unittest.TestCase):
    def test_workers_serialize_and_release_the_session(self):
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(['javac','-d',td,str(ROOT/'tools/native/android/PreparationSession.java'),
                            str(ROOT/'tests/android/PreparationSessionCheck.java')],check=True,capture_output=True)
            result=subprocess.run(['java','-cp',td,'org.triaevum.android.PreparationSessionCheck',str(Path(td)/'data')],
                                  check=True,capture_output=True,text=True)
            self.assertEqual(result.stdout.strip(),'PASS')
            command=['java','-cp',td,'org.triaevum.android.PreparationSessionCheck',str(Path(td)/'data')]
            owner=subprocess.Popen(command+['hold'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                self.assertEqual(owner.stdout.readline().strip(),'READY')
                peer=subprocess.run(command+['probe'],check=True,capture_output=True,text=True,timeout=10)
                self.assertEqual(peer.stdout.strip(),'BLOCKED')
            finally:
                owner.communicate('release\n',timeout=10)
            self.assertEqual(owner.returncode,0)
