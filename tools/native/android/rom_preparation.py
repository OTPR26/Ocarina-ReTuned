"""Android implementation of the shared local ROM preparation pipeline.

The app supplies its APK-installed compiler executables and a hash-verified,
neutral SDK. No Git, CMake, desktop companion, prepared title, or network ROM
service is used by this backend.
"""
from contextlib import redirect_stderr, redirect_stdout
import ctypes
import gc
import json
import os
from pathlib import Path
import sys

# The bundled project has the same layout as the desktop preparation kit.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rom_setup import RomSetup, SetupError, digest, load_module, verify_preparation_source


class AndroidRomSetup(RomSetup):
    def __init__(self, *, sdk, compiler, linker, runtime_library, **options):
        super().__init__(host=compiler, readelf='unused', **options)
        self.sdk = Path(sdk).resolve()
        self.compiler = Path(compiler).resolve()
        self.linker = Path(linker).resolve()
        self.runtime_library = Path(runtime_library).resolve()
        self.environment['LD_LIBRARY_PATH'] = str(self.sdk / 'compiler-libraries')
        self.specification = None

    def asset(self, value):
        relative = Path(value)
        if relative.is_absolute() or '..' in relative.parts:
            raise SetupError('Android SDK path escapes its directory')
        result = (self.sdk / relative).resolve()
        if not result.is_relative_to(self.sdk):
            raise SetupError('Android SDK link escapes its directory')
        return result

    def preflight(self):
        import capstone
        verify_preparation_source(self.engine)
        for path in (self.ips, self.elf, self.compiler, self.linker, self.runtime_library):
            if not path.is_file():
                raise SetupError('The Android preparation tools are incomplete.')
        self.specification = json.loads((self.sdk / 'sdk.json').read_text())
        if self.specification.get('format') != 'retuned_android_title_sdk_v1':
            raise SetupError('Unsupported Android preparation SDK')
        for name, expected in self.specification['files'].items():
            if digest(self.asset(name)) != expected:
                raise SetupError('An Android preparation tool failed its integrity check.')

    def run(self, command, cwd=None):
        # The same translator runs inside embedded Python on Android. Executing
        # a desktop Python binary or a script from writable storage is unnecessary.
        if command[0] == sys.executable and len(command) > 1:
            script = Path(command[1])
            arguments = list(map(str, command[2:]))
            self.checkpoint('translating', 'Preparing your game locally...')
            with redirect_stdout(self.log), redirect_stderr(self.log):
                if script.name == 'whole_aot_program.py':
                    translator = load_module('_retuned_android_ir', script)
                    if translator.main(arguments):
                        raise SetupError('Local game translation failed.')
                elif script.name in ('generate_title_sources.py', 'generate_whole_aot_cpp.py'):
                    # Avoid the upstream CLI's developer operational-input
                    # defaults. Every game path comes from this setup transaction.
                    from whole_aot_cpp import generate
                    def option(flag):
                        return Path(arguments[arguments.index(flag) + 1])
                    generate(option('--program'), option('--selection'), option('--code'),
                        option('--output'), shard_count=64, shard_strategy='stable',
                        region_entries=frozenset(), memory_entries=frozenset(), local_state=False)
                else:
                    raise SetupError('Unsupported preparation stage')
            gc.collect()
            return
        return super().run(command, cwd)

    def compile_title(self, work, generated):
        build = work / 'build'
        build.mkdir()
        specification = self.specification
        includes = [self.asset(name) for name in specification['include_directories']]
        includes.append(generated)
        sources = sorted(generated.glob('*.cpp'))
        # Keep the plugin and generated units on the same verified header tree.
        # Compiling the other copy in self.engine defeats #pragma once when
        # its quoted includes meet generated units using the SDK copy.
        sources.append(self.asset('engine/tools/oot3d/native_game_runtime/triaevum_title_whole_aot_plugin.cpp'))
        objects = []
        for number, source in enumerate(sources):
            self.checkpoint('compiling', f'Building native game module: {number + 1} of {len(sources)}...')
            target = build / (str(number) + '.o')
            command = [self.compiler, '--target=aarch64-linux-android29',
                '--sysroot=' + str(self.asset(specification['sysroot'])),
                '-resource-dir=' + str(self.asset(specification['resource_directory'])),
                '-std=c++20', '-O1', '-g0', '-fPIC', '-fvisibility=hidden',
                '-fvisibility-inlines-hidden', '-ffp-contract=off', '-fexceptions',
                '-DOOT3D_NATIVE_GENERATED_WHOLE_AOT=1', '-c', source, '-o', target]
            for include in includes:
                command += ['-I', include]
            self.run(command)
            objects.append(target)
        library = build / 'triaevum_title_aot.so'
        system = self.asset(specification['system_libraries'])
        command = [self.linker, '-flavor', 'gnu', '-shared', '--hash-style=gnu',
            '--eh-frame-hdr', '--no-undefined', '-z', 'max-page-size=16384',
            '-soname', library.name, '-o', library, system / 'crtbegin_so.o', *objects,
            self.asset(specification['support_archive']), self.runtime_library,
            self.asset(specification['builtins_archive']), self.asset(specification['unwind_archive']),
            '-L', system, '-lc', '-lm', '-ldl', system / 'crtend_so.o']
        self.run(command)
        library.chmod(0o400)
        return library

    def verify_title(self, library):
        class Program(ctypes.Structure):
            _fields_ = [('abi', ctypes.c_uint32), ('size', ctypes.c_uint32),
                ('entries', ctypes.c_void_p), ('entry_count', ctypes.c_size_t),
                ('execute', ctypes.c_void_p), ('active', ctypes.c_void_p),
                ('observable_exit', ctypes.c_void_p), ('memory_visibility', ctypes.c_uint32)]
        handle = ctypes.CDLL(str(library), mode=ctypes.RTLD_LOCAL)
        query = handle.triaevum_title_whole_aot_query
        query.argtypes = [ctypes.c_uint32]
        query.restype = ctypes.POINTER(Program)
        result = query(2)
        if not result:
            raise SetupError('The generated game module has an incompatible ABI.')
        program = result.contents
        valid = (program.abi == 2 and program.size == ctypes.sizeof(Program)
            and program.memory_visibility == 3 and program.entry_count > 0
            and program.entries and program.execute and program.active
            and program.observable_exit and not query(1))
        if not valid:
            raise SetupError('The generated game module failed verification.')
        # Keep this local module alive through activation; gameplay reuses the
        # same immutable file. The global host/plugin selection is not changed.
        self.verified_module = handle
