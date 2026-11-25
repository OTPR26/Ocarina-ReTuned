import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare_android_app', ROOT/'tools/native/prepare_android_app.py')
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


class AndroidDocumentsTests(unittest.TestCase):
    def test_activity_patch_is_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            activity = Path(directory)/'RetunedGameActivity.java'
            activity.write_text('''class RetunedGameActivity {
    private TextureFolder retunedTextures;
    void onCreate(){
        retunedTextures=new TextureFolder(this);
    }
    void onActivityResult(int request,int result,Intent data){
        if(request==TextureFolder.REQUEST)return;
    }
}''')
            patch.install_randomizer_documents(activity)
            first = activity.read_text()
            patch.install_randomizer_documents(activity)
            self.assertEqual(first, activity.read_text())
            self.assertEqual(first.count('new RandomizerDocuments(this)'), 1)
            self.assertLess(first.index('retunedRuns.result'), first.index('request==TextureFolder.REQUEST'))
            self.assertTrue(activity.with_name('RandomizerDocuments.java').is_file())

    def test_android_stream_limits(self):
        sdk = Path(os.environ.get('ANDROID_HOME', Path.home()/'Library/Android/sdk'))
        jar = sdk/'platforms/android-35/android.jar'
        java = Path('/Applications/Android Studio.app/Contents/jbr/Contents/Home/bin')
        if not jar.exists() or not (java/'javac').exists():
            self.skipTest('Android SDK and JDK are not available')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            test = root/'DocumentStreamTest.java'
            test.write_text('''package org.triaevum.android;
import java.io.*;
import java.util.Arrays;
public class DocumentStreamTest {
 public static void main(String[] args) throws Exception {
  byte[] bytes="run bytes: 🎲".getBytes("UTF-8");
  if(!Arrays.equals(bytes,RandomizerDocuments.readBounded(new ByteArrayInputStream(bytes))))throw new AssertionError();
  int limit=10*1024*1024;
  if(RandomizerDocuments.readBounded(new ByteArrayInputStream(new byte[limit])).length!=limit)throw new AssertionError();
  for(int size:new int[]{0,limit+1}) {
   try{RandomizerDocuments.readBounded(new ByteArrayInputStream(new byte[size]));throw new AssertionError();}
   catch(IOException expected){}
  }
  InputStream failing=new InputStream(){public int read() throws IOException{throw new IOException("provider failed");}};
  try{RandomizerDocuments.readBounded(failing);throw new AssertionError();}catch(IOException expected){}
 }
}''')
            subprocess.run([str(java/'javac'), '-classpath', str(jar), '-d', str(root),
                            str(ROOT/'tools/native/android/RandomizerDocuments.java'), str(test)], check=True)
            subprocess.run([str(java/'java'), '-cp', os.pathsep.join([str(root), str(jar)]),
                            'org.triaevum.android.DocumentStreamTest'], check=True)


if __name__ == '__main__':
    unittest.main()
