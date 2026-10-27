import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('linux_rom_setup', PROJECT / 'tools/native/rom_setup.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


@unittest.skipUnless(sys.platform.startswith('linux') and shutil.which('cmake') and
                     shutil.which('ninja') and (shutil.which(os.environ.get('CXX', 'c++'))),
                     'requires Linux preparation tools')
class LinuxPreparationAbi(unittest.TestCase):
    def check(self, arguments=(), environment=None):
        instance = SimpleNamespace(cmake=shutil.which('cmake'), cmake_args=list(arguments),
                                   environment=environment or dict(os.environ))
        setup.RomSetup.verify_linux_compiler(instance)

    def test_system_libstdcxx_needs_no_rom_or_runtime_tree(self):
        self.check()

    def test_old_string_abi_is_rejected(self):
        with self.assertRaisesRegex(setup.SetupError, 'libstdc'):
            self.check(['-DCMAKE_CXX_FLAGS=-D_GLIBCXX_USE_CXX11_ABI=0'])

    def test_debug_containers_are_rejected(self):
        with self.assertRaisesRegex(setup.SetupError, 'libstdc'):
            self.check(['-DCMAKE_CXX_FLAGS=-D_GLIBCXX_DEBUG'])

    @unittest.skipUnless(os.environ.get('RETUNED_TEST_LIBCXX_CXX'), 'requires a libc++ compiler')
    def test_libcxx_compiler_is_rejected_before_title_build(self):
        environment = dict(os.environ, CXX=os.environ.get('RETUNED_TEST_LIBCXX_CXX', ''))
        with self.assertRaisesRegex(setup.SetupError, 'libstdc'):
            self.check(environment=environment)

    def test_direct_title_configuration_cannot_bypass_check(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(['cmake', '-S', str(PROJECT / 'tools/native/title'),
                '-B', directory, '-G', 'Ninja',
                '-DCMAKE_CXX_FLAGS=-D_GLIBCXX_USE_CXX11_ABI=0'],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('libstdc++', result.stdout + result.stderr)
            self.assertNotIn('pinned runtime source checkout is required', result.stderr)


if __name__ == '__main__':
    unittest.main()
