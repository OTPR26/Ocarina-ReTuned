import importlib.util
from pathlib import Path, PurePosixPath
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('windows_toolchain',
    Path(__file__).resolve().parents[1] / 'tools/native/stage_windows_toolchain.py')
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)


class WindowsToolchainStaging(unittest.TestCase):
    def test_omits_unused_store_signing_templates(self):
        self.assertFalse(tools.selected('cmake', PurePosixPath('share/cmake/Templates/Windows/Windows_TemporaryKey.pfx')))

    def test_unverified_archive_never_creates_tool_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / 'compiler.zip'
            archive.write_bytes(b'unverified toolchain')
            with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                tools.stage({'llvm': archive}, root / 'notice', root / 'output')
            self.assertFalse((root / 'output').exists())

    def test_existing_toolchain_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'keep').write_bytes(b'existing')
            with self.assertRaisesRegex(ValueError, 'overwrite'):
                tools.stage({}, root / 'notice', root)
            self.assertEqual((root / 'keep').read_bytes(), b'existing')

    def test_only_needed_architecture_and_tools_are_selected(self):
        for path in ('bin/x86_64-w64-mingw32-clang++.exe', 'bin/libclang-cpp.dll',
                     'lib/clang/23/include/stddef.h', 'x86_64-w64-mingw32/share/mingw32/COPYING'):
            self.assertTrue(tools.selected('llvm', PurePosixPath(path)), path)
        for path in ('aarch64-w64-mingw32/lib/libc++.a', 'bin/lldb.exe',
                     'python/bin/python.exe', 'bin/i686-w64-mingw32-clang.exe', 'bin/clangd.exe',
                     'bin/libffi-8.dll'):
            self.assertFalse(tools.selected('llvm', PurePosixPath(path)), path)

    def test_cmake_original_dependency_notices_survive_documentation_trimming(self):
        for path in ('doc/cmake/LICENSE.rst', 'doc/cmake/cmcurl/COPYING',
                     'doc/cmake/cmlibuv/LICENSE', 'doc/cmake/cmsys/Copyright.txt',
                     'doc/cmake/cmcppdap/NOTICE'):
            self.assertTrue(tools.selected('cmake', PurePosixPath(path)), path)
        self.assertFalse(tools.selected('cmake', PurePosixPath('doc/cmake/html/index.html')))

    def test_arm64_selection_excludes_incompatible_x64_target_libraries(self):
        for path in ('aarch64-w64-mingw32/lib/libc++.a',
                     'bin/aarch64-w64-mingw32-clang++.exe', 'bin/libclang-cpp.dll'):
            self.assertTrue(tools.selected('llvm', PurePosixPath(path), 'arm64'), path)
        for path in ('x86_64-w64-mingw32/lib/libc++.a',
                     'bin/x86_64-w64-mingw32-clang++.exe', 'bin/arm64ec-w64-mingw32-clang.exe'):
            self.assertFalse(tools.selected('llvm', PurePosixPath(path), 'arm64'), path)
        with self.assertRaises(ValueError):
            tools.selected('llvm', PurePosixPath('bin/clang.exe'), 'unknown')
