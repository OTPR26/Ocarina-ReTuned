"""Android implementation of the shared local ROM preparation pipeline.

The app supplies its APK-installed compiler executables and a hash-verified,
neutral SDK. No Git, CMake, desktop companion, prepared title, or network ROM
service is used by this backend.
"""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import redirect_stderr, redirect_stdout
import ctypes
import gc
import json
import os
from pathlib import Path
import sys
import threading
import time

# The bundled project has the same layout as the desktop preparation kit.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preparation_cache import fingerprint
from rom_setup import RomSetup, SetupCancelled, SetupError, digest, load_module, verify_preparation_source, write_json


MIB = 1024 * 1024
COMPILER_MEMORY = 1024 * MIB


def memory_snapshot():
    """Use current available RAM, including reclaimable cache, rather than free RAM."""
    try:
        fields = {}
        for line in Path('/proc/meminfo').read_text().splitlines():
            name, _, value = line.partition(':')
            if name in ('MemTotal', 'MemAvailable'):
                fields[name] = int(value.split()[0]) * 1024
        return fields['MemTotal'], fields['MemAvailable']
    except (OSError, ValueError, IndexError, KeyError):
        return 0, 0


def compilation_workers(cpu_count, total, available, requested=4):
    """Keep small devices serial; cap the foreground compiler at four workers."""
    reserve = max(768 * MIB, total // 8)
    budget = max(0, min(available - reserve, total * 2 // 5))
    return max(1, min(4, max(1, cpu_count or 1), requested, budget // COMPILER_MEMORY))


class CompilationCancellation:
    """Stop sibling compiler processes on failure without changing the user's cancel file."""
    def __init__(self, user):
        self.user = user
        self.stop = threading.Event()

    def is_set(self):
        return self.stop.is_set() or self.user.is_set()

    def wait(self, seconds):
        deadline = time.monotonic() + seconds
        while not self.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            self.stop.wait(min(remaining, 0.05))
        return True


class AndroidRomSetup(RomSetup):
    def __init__(self, *, sdk, compiler, linker, runtime_library, **options):
        requested = options.pop('jobs', 4)
        super().__init__(host=compiler, readelf='unused', jobs=requested, **options)
        self.sdk = Path(sdk).resolve()
        self.compiler = Path(compiler).resolve()
        self.linker = Path(linker).resolve()
        self.runtime_library = Path(runtime_library).resolve()
        self.environment['LD_LIBRARY_PATH'] = str(self.sdk / 'compiler-libraries')
        self.specification = None
        self._timed_stage = None
        self.stage_timings = []
        self.compilation_statistics = {}

    def checkpoint(self, stage, message, completed=None, total=None):
        if getattr(self, '_collect_timings', False) and stage != self._timed_stage:
            self.finish_stage()
            self._timed_stage, self._stage_started = stage, time.monotonic()
        if completed is None:
            super().checkpoint(stage, message)
        else:
            self.report_units(stage, message, completed, total)

    def report_units(self, stage, message, completed, total):
        if self.cancel.is_set():
            raise SetupCancelled('Setup cancelled. Your ROM and saves are unchanged.')
        self.progress({'stage': stage, 'message': message, 'completed': completed, 'total': total})

    def finish_stage(self):
        if self._timed_stage is not None:
            self.stage_timings.append({'stage': self._timed_stage,
                'seconds': round(time.monotonic() - self._stage_started, 3)})
            self._timed_stage = None

    def _prepare(self, rom, root, work):
        self.stage_timings = []
        self._collect_timings = True
        outcome = 'failed'
        started = time.monotonic()
        try:
            result = super()._prepare(rom, root, work)
            outcome = 'complete'
            return result
        finally:
            self.finish_stage()
            self._collect_timings = False
            # Diagnostic timings contain no ROM paths, source, or game data.
            # A diagnostic write must not invalidate a successful activation.
            try:
                write_json(root / 'setup-timings.json', {
                    'format': 'retuned_android_preparation_timings_v1', 'outcome': outcome,
                    'seconds': round(time.monotonic() - started, 3),
                    'stages': self.stage_timings, 'compilation': self.compilation_statistics})
            except OSError:
                pass

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
            generating = script.name in ('generate_title_sources.py', 'generate_whole_aot_cpp.py')
            self.checkpoint('generating' if generating else 'translating',
                'Generating native game code locally...' if generating else 'Preparing your game locally...')
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
        objects = [build / (str(number) + '.o') for number in range(len(sources))]
        cache = getattr(self, 'cache', None)
        compiler_identity = None
        if cache is not None:
            compiler_identity = fingerprint({'format': 'retuned-android-objects-v1',
                'sdk': digest(self.sdk / 'sdk.json'), 'compiler': digest(self.compiler),
                'include_directories': specification['include_directories'],
                'defines': ['OOT3D_NATIVE_GENERATED_WHOLE_AOT=1'],
                'headers': {p.name: digest(p) for p in generated.glob('*.h')},
                'flags': ['aarch64-linux-android29', 'c++20', '-O1', '-g0', '-fPIC',
                          '-fvisibility=hidden', '-fvisibility-inlines-hidden', '-ffp-contract=off', '-fexceptions']})

        total_memory, available = memory_snapshot()
        workers = compilation_workers(os.cpu_count(), total_memory, available, self.jobs)
        self.compilation_statistics = {'workers': workers, 'units': len(sources),
            'available_bytes': available, 'physical_bytes': total_memory,
            'bytes_per_worker': COMPILER_MEMORY, 'reused_units': 0}
        self.module_cache_key = None
        if cache is not None:
            self.module_cache_key = fingerprint({'format': 'retuned-android-module-v1',
                'compiler': compiler_identity, 'linker': digest(self.linker), 'runtime': digest(self.runtime_library),
                'sources': {p.name: digest(p) for p in sources}})
            cached = build / 'cached-module'
            if cache.restore(self.module_cache_key, cached, required={'triaevum_title_aot.so'}):
                library = build / 'triaevum_title_aot.so'
                (cached / library.name).replace(library)
                cached.rmdir()
                self.compilation_statistics['reused_units'] = len(sources)
                self.checkpoint('compiling', 'Reusing the verified native game module on this device…', len(sources), len(sources))
                return library
        self.checkpoint('compiling', f'Building native game module: 0 of {len(sources)} ({workers} at a time)...', 0, len(sources))
        cancellation = CompilationCancellation(self.cancel)
        original_cancel, self.cancel = self.cancel, cancellation
        def compile_one(number):
            source, target = sources[number], objects[number]
            key = fingerprint({'compiler': compiler_identity, 'name': source.name, 'source': digest(source)}) if cache is not None else None
            restore = build / ('cached-' + str(number))
            if cache is not None and cache.restore(key, restore, required={'unit.o'}):
                (restore / 'unit.o').replace(target)
                restore.rmdir()
                return True
            command = [self.compiler, '--target=aarch64-linux-android29',
                '--sysroot=' + str(self.asset(specification['sysroot'])),
                '-resource-dir=' + str(self.asset(specification['resource_directory'])),
                '-std=c++20', '-O1', '-g0', '-fPIC', '-fvisibility=hidden',
                '-fvisibility-inlines-hidden', '-ffp-contract=off', '-fexceptions',
                '-DOOT3D_NATIVE_GENERATED_WHOLE_AOT=1', '-c', source, '-o', target]
            for include in includes:
                command += ['-I', include]
            self.run(command)
            if cache is not None:
                cache.store(key, {'unit.o': target})
            return False
        try:
            # Only a bounded batch is submitted. Cancellation/failure kills and
            # joins active subprocesses before the setup transaction is removed.
            with ThreadPoolExecutor(max_workers=workers) as pool:
                active = set()
                next_source = completed = 0
                try:
                    while next_source < len(sources) or active:
                        while next_source < len(sources) and len(active) < workers:
                            if cancellation.is_set():
                                self.checkpoint('compiling', 'Stopping setup...')
                            active.add(pool.submit(compile_one, next_source))
                            next_source += 1
                        done, active = wait(active, return_when=FIRST_COMPLETED)
                        for future in done:
                            if future.result():
                                self.compilation_statistics['reused_units'] += 1
                            completed += 1
                            self.checkpoint('compiling', f'Building native game module: {completed} of {len(sources)} ({workers} at a time)...', completed, len(sources))
                except BaseException:
                    cancellation.stop.set()
                    for future in active:
                        future.cancel()
                    raise
        finally:
            self.cancel = original_cancel
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
        if getattr(self, 'module_cache_key', None) is not None:
            self.cache.store(self.module_cache_key, {library.name: library})
