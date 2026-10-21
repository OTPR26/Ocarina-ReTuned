"""Native regression for a generated module and its SDK header identity."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'tools/native/android/rom_preparation.py'
spec = importlib.util.spec_from_file_location('android_preparation', MODULE)
android = importlib.util.module_from_spec(spec)
spec.loader.exec_module(android)


@unittest.skipUnless(shutil.which('c++'), 'A native C++ compiler is required')
class AndroidPreparationHeaders(unittest.TestCase):
    def test_plugin_and_generated_units_share_one_header_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            relative = Path('engine/tools/oot3d/native_game_runtime')
            sdk = root / 'sdk'
            runtime = sdk / relative
            other = root / relative
            generated = root / 'generated'
            for directory in (runtime, other, generated):
                directory.mkdir(parents=True)
            # The plugin must resolve quoted includes to the same SDK copy
            # as the generated unit. Give the alternate copy a harmless extra
            # declaration: GCC may coalesce byte-identical files, while Clang
            # exposes the Android failure even when their contents match.
            for directory in (runtime, other):
                (directory / 'runtime.h').write_text('#pragma once\nstruct Frame { int value; };\n')
                (directory / 'triaevum_title_whole_aot_plugin.cpp').write_text(
                    '#include "runtime.h"\n#include "generated.h"\nint plugin() { return sizeof(Frame); }\n')
            with (other / 'runtime.h').open('a') as stream:
                stream.write('struct AlternateHeaderIdentity {};\n')
            (generated / 'generated.h').write_text('#pragma once\n#include "runtime.h"\n')
            (generated / 'generated.cpp').write_text('#include "generated.h"\nint generated() { return sizeof(Frame); }\n')
            compiler = shutil.which('c++')
            mismatched = subprocess.run([compiler, '-std=c++20', '-fsyntax-only',
                '-I', str(runtime), '-I', str(generated),
                str(other / 'triaevum_title_whole_aot_plugin.cpp')], capture_output=True, text=True)
            self.assertNotEqual(mismatched.returncode, 0)
            self.assertIn('redefinition', mismatched.stderr)

            class LocalCompiler(android.AndroidRomSetup):
                def run(self, command, cwd=None):
                    if command[0] == self.compiler:
                        flags = [str(value) for value in command[1:] if not str(value).startswith(
                            ('--target=', '--sysroot=', '-resource-dir='))]
                        subprocess.run([compiler, *flags], check=True, capture_output=True)
                    else:
                        output = command[command.index('-o') + 1]
                        objects = [str(value) for value in command if str(value).endswith('.o') and Path(value).is_file()]
                        subprocess.run([compiler, '-shared', *objects, '-o', str(output)], check=True, capture_output=True)

            worker = LocalCompiler(sdk=sdk, engine=root / 'engine', compiler=compiler,
                linker=root / 'linker', runtime_library=root / 'libc++.so', ips=root / 'mod.ips', elf=root / 'mod.elf')
            worker.specification = {'include_directories': [str(relative)], 'sysroot': 'sysroot',
                'resource_directory': 'resource', 'system_libraries': 'system', 'support_archive': 'support.a',
                'builtins_archive': 'builtins.a', 'unwind_archive': 'unwind.a'}
            self.assertTrue(worker.compile_title(root, generated).is_file())
