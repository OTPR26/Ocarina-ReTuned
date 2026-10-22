"""A diagnostic profile must not fall back to the player's default data root."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(sys.platform == 'darwin', 'Mac executable bootstrap')
class MacLauncherTests(unittest.TestCase):
    def test_reexec_keeps_explicit_relative_profile_and_its_working_directory(self):
        with tempfile.TemporaryDirectory(prefix='retuned-launch-') as temporary:
            root = Path(temporary).resolve()
            executable = root / 'Test.app/Contents/MacOS/retuned-native'
            executable.parent.mkdir(parents=True)
            stub = root / 'stub.cpp'
            stub.write_text('#include <cstdio>\n#include <filesystem>\n'
                'int RetunedMacNativeMain(int argc,char**argv){'
                'std::puts(std::filesystem::current_path().c_str());'
                'for(int i=1;i<argc;++i)std::puts(argv[i]);return 0;}\n')
            subprocess.run(['clang++', '-std=c++20', str(ROOT/'tools/native/macos_launcher.cpp'),
                            str(stub), '-o', str(executable)], check=True, capture_output=True)
            env = dict(os.environ)
            env.pop('RETUNED_MAC_BOOTSTRAPPED', None)
            result = subprocess.check_output([str(executable), '--launch-profile', 'separate data/profile.json'],
                cwd=root, env=env, text=True)
            self.assertEqual(result.splitlines(), [str(root/'separate data'), '--launch-profile', str(root/'separate data/profile.json')])
            diagnostic = subprocess.check_output([str(executable), '--product-info'], cwd=root, env=env, text=True)
            self.assertEqual(diagnostic.splitlines(), [str(root), '--product-info'])
            missing = subprocess.run([str(executable), '--launch-profile'], cwd=root, env=env, capture_output=True)
            self.assertEqual(missing.returncode, 2)


if __name__=='__main__':unittest.main()
