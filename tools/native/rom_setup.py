#!/usr/bin/env python3
"""Local ROM-to-native preparation. Generated files never leave this machine.

The preparation kit contains translation tools and our HUD mod; it must match
this application's tested revision. No prepared title is downloaded. Desktop
C++ build tools are required until a bundled toolchain is available.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import gc
import importlib.util
import json
import os
from pathlib import Path
import platform
import signal
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid

PROJECT = Path(__file__).resolve().parents[2]
RUNTIME_REVISION = '17218b0cfdb944645bb5cde5249f313dca7e53ce'
CANONICAL_CODE = '16a6b0aa4c4784680220a6f780f7f8a73cfb205557aa9f9f0e705179e0613220'
CANONICAL_ROMFS = 'dae620379c805e96a6187c212dc2b177cf5fdb0c184d526a06ebaeeaa481aa56'


class SetupError(ValueError):
    pass


class SetupCancelled(SetupError):
    pass


def windows_build_environment(environment):
    """Discover installed C++ tools for normal GUI launches, without global changes."""
    result = {name.upper(): value for name, value in environment.items()}
    installer = Path(result.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)')) / 'Microsoft Visual Studio/Installer/vswhere.exe'
    if not installer.is_file():
        return result
    probe = subprocess.run([str(installer), '-latest', '-products', '*', '-requires',
        'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath', '-utf8'],
        capture_output=True, text=True, encoding='utf-8', check=True, env=result)
    location = probe.stdout.strip()
    if not location:
        return result
    installation = Path(location)
    vcvars = installation / 'VC/Auxiliary/Build/vcvars64.bat'
    if vcvars.is_file() and result.get('VSCMD_ARG_TGT_ARCH') != 'x64':
        child = dict(result, RETUNED_VCVARS=str(vcvars))
        # cmd uses its own quote rules; list2cmdline on the batch expression
        # would introduce literal backslashes before its internal quotes.
        command = subprocess.list2cmdline([result.get('COMSPEC', 'cmd.exe')])
        command += ' /d /u /s /c call "%RETUNED_VCVARS%" >nul && set'
        initialized = subprocess.run(command, capture_output=True, text=True,
            encoding='utf-16-le', check=True, env=child)
        for line in initialized.stdout.splitlines():
            name, separator, value = line.partition('=')
            if separator and name and not name.startswith('=') and name.upper() != 'RETUNED_VCVARS':
                result[name.upper()] = value
    cmake_root = installation / 'Common7/IDE/CommonExtensions/Microsoft/CMake'
    for directory, executable in ((cmake_root / 'CMake/bin', 'cmake.exe'), (cmake_root / 'Ninja', 'ninja.exe')):
        if (directory / executable).is_file():
            result['PATH'] = result.get('PATH', '') + ';' + str(directory)
    return result


def portable_windows_environment(environment, tools):
    """Use only the app's compiler/build tools and Windows system executables."""
    root = Path(tools).resolve()
    result = {name.upper(): value for name, value in environment.items()}
    for name in ('INCLUDE', 'LIB', 'LIBPATH', 'CC', 'CXX', 'CFLAGS', 'CXXFLAGS',
                 'LDFLAGS', 'CMAKE_TOOLCHAIN_FILE', 'VCTOOLSINSTALLDIR', 'VCINSTALLDIR',
                 'VSINSTALLDIR', 'WINDOWSSDKDIR', 'VSCMD_ARG_TGT_ARCH'):
        result.pop(name, None)
    directories = [root / 'llvm/bin', root / 'cmake/bin', root / 'ninja']
    for executable in (directories[0] / 'x86_64-w64-mingw32-clang++.exe',
                       directories[1] / 'cmake.exe', directories[2] / 'ninja.exe'):
        if not executable.is_file():
            raise SetupError('The bundled Windows preparation tools are incomplete.')
    system = Path(result.get('SYSTEMROOT', r'C:\Windows')) / 'System32'
    result['PATH'] = ';'.join(map(str, [*directories, system]))
    return result


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def verify_preparation_source(engine):
    """Accept a pinned development checkout or a sealed minimal runtime tree."""
    engine = Path(engine).resolve()
    if (engine / '.git').exists():
        revision = subprocess.check_output(['git', '-C', str(engine), 'rev-parse', 'HEAD'], text=True).strip()
        if revision != RUNTIME_REVISION:
            raise SetupError('The preparation tools do not match this app.')
        return
    try:
        metadata = json.loads((engine / 'preparation-runtime.json').read_text())
        if (metadata.get('format') != 'retuned_preparation_runtime_v1' or
                metadata.get('source_revision') != RUNTIME_REVISION):
            raise ValueError('Unsupported preparation source')
        files = metadata['files']
        if not isinstance(files, dict) or not files:
            raise ValueError('Empty preparation source')
        for name, expected in files.items():
            relative = Path(name)
            path = (engine / relative).resolve()
            if relative.is_absolute() or '..' in relative.parts or not path.is_relative_to(engine):
                raise ValueError('Preparation source path escapes its tree')
            if (engine / relative).is_symlink() or digest(path) != expected:
                raise ValueError('Preparation source checksum mismatch')
        actual = {p.relative_to(engine).as_posix() for p in engine.rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts and p.name != 'preparation-runtime.json'}
        if actual != set(files):
            raise ValueError('Unexpected preparation source files')
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise SetupError('The preparation source is incomplete or failed its integrity check.') from error


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@contextmanager
def installation_transaction(data_root):
    """Serialize setup and never expose partially prepared game data.

    Lock files are deliberately not auto-stolen: PID reuse and network file
    systems make that unsafe. An interrupted setup can be retried after the
    application explains how to remove its stale lock.
    """
    root = Path(data_root).expanduser().absolute()
    root.mkdir(parents=True, exist_ok=True)
    lock = root / '.rom-setup.lock'
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise SetupError('Another setup is running. If it was interrupted, close the app and remove .rom-setup.lock before retrying.') from error
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump({'pid': os.getpid(), 'started': time.time()}, stream)
        with tempfile.TemporaryDirectory(prefix='.rom-setup-', dir=root) as temporary:
            yield root, Path(temporary)
    finally:
        lock.unlink(missing_ok=True)


def activate(root, stage, installation_id, make_profile, profile_root=None):
    """Publish immutable prepared data, then atomically switch the launch profile.

    Preferences, controls and saves are outside this tree and are never written.
    The previous launch profile remains valid if preparation or activation fails.
    """
    if not installation_id.isalnum():
        raise SetupError('Invalid installation identity')
    installations = root / 'installations'
    if installations.is_symlink():
        raise SetupError('Installation directory must not be a symbolic link')
    installations.mkdir(exist_ok=True)
    target = installations / installation_id
    if target.exists() or target.is_symlink():
        raise SetupError('This installation already exists')
    profile_root = Path(profile_root) if profile_root is not None else root
    profile_root.mkdir(parents=True, exist_ok=True)
    profile = profile_root / 'native-launch.json'
    if profile.is_symlink():
        raise SetupError('Launch profile must not be a symbolic link')
    temporary_profile = profile_root / ('.launch-' + uuid.uuid4().hex + '.json')
    try:
        write_json(temporary_profile, make_profile(target))
        with temporary_profile.open('rb') as stream:
            os.fsync(stream.fileno())
        stage.rename(target)
        try:
            os.replace(temporary_profile, profile)
        except BaseException:
            target.rename(stage)
            raise
    finally:
        temporary_profile.unlink(missing_ok=True)
    return target


class RomSetup:
    def __init__(self, *, engine, ips, elf, host, readelf='arm-none-eabi-readelf',
                 cmake='cmake', cmake_args=(), jobs=2, progress=None, cancel=None, profile_root=None,
                 windows_tools=None):
        self.engine = Path(engine).resolve()
        self.ips, self.elf, self.host = map(lambda p: Path(p).resolve(), (ips, elf, host))
        self.readelf, self.cmake = str(readelf), str(cmake)
        self.cmake_args, self.jobs = list(cmake_args), max(1, min(int(jobs), 8))
        self.progress = progress or (lambda event: None)
        self.cancel = cancel or threading.Event()
        self.log = None
        self.profile_root = Path(profile_root).resolve() if profile_root is not None else None
        self.windows_tools = Path(windows_tools).resolve() if windows_tools is not None else None
        self.environment = dict(os.environ)
        self.environment['PYTHONDONTWRITEBYTECODE'] = '1'
        if sys.platform == 'win32':
            self.environment = (portable_windows_environment(self.environment, windows_tools)
                if windows_tools is not None else windows_build_environment(self.environment))
        if sys.platform == 'darwin':
            self.environment['RETUNED_MAC_BOOTSTRAPPED'] = '1'

    def checkpoint(self, stage, message):
        if self.cancel.is_set():
            raise SetupCancelled('Setup cancelled. Existing game data and saves were preserved.')
        self.progress({'stage': stage, 'message': message})

    def run(self, command, cwd=None):
        if self.cancel.is_set():
            raise SetupCancelled('Setup cancelled. Existing game data and saves were preserved.')
        with subprocess.Popen(list(map(str, command)), cwd=cwd, stdout=self.log,
                              stderr=subprocess.STDOUT, env=self.environment, start_new_session=os.name != 'nt') as process:
            while process.poll() is None:
                if self.cancel.wait(0.2):
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        if os.name == 'nt':
                            process.kill()
                        else:
                            os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    raise SetupCancelled('Setup cancelled. Existing game data and saves were preserved.')
            if process.returncode:
                raise SetupError('A local preparation step failed. See setup.log for details; your existing game data and saves were preserved.')

    def preflight(self):
        for path in (self.ips, self.elf, self.host):
            if not path.is_file():
                raise SetupError('The local preparation kit is incomplete.')
        verify_preparation_source(self.engine)
        if self.windows_tools is not None:
            try:
                compiler = json.loads((self.windows_tools / 'toolchain-manifest.json').read_text())
                host = json.loads(self.host.with_name('preparation-abi.json').read_text())
                if (compiler['abi'] != 'x86_64-llvm-mingw-ucrt-20261006' or
                        host['abi'] != compiler['abi'] or host['host_sha256'] != digest(self.host)):
                    raise ValueError('Compiler ABI mismatch')
            except (OSError, ValueError, KeyError) as error:
                raise SetupError('The bundled preparation tools do not match this Windows app.') from error
        try:
            import capstone
        except ImportError as error:
            raise SetupError('The preparation runtime is missing its Capstone dependency.') from error
        subprocess.run([str(self.host), '--product-info'], check=True, env=self.environment,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for tool in (self.cmake, 'ninja'):
            if shutil.which(tool, path=self.environment.get('PATH')) is None:
                raise SetupError('Required local build tool is missing: ' + Path(tool).name)

    def prepare(self, rom, data_root):
        self.checkpoint('checking', 'Checking the ROM and local preparation tools…')
        self.preflight()
        rom = Path(rom).expanduser().resolve()
        if not rom.is_file():
            raise SetupError('Choose a decrypted Ocarina of Time 3D USA cartridge dump (.3ds or .cci).')
        with installation_transaction(data_root) as (root, work):
            with (root / 'setup.log').open('w', encoding='utf-8') as log:
                self.log = log
                return self._prepare(rom, root, work)

    def _prepare(self, rom, root, work):
        engine = self.engine
        a32 = engine / 'tools/oot3d/native_a32_runtime'
        release = engine / 'tools/triaevum_release'
        # Explicit import roots prevent upstream operational-input defaults from
        # locating a developer's private game files.
        sys.path[:0] = [str(a32), str(release), str(PROJECT / 'tools/reframed')]
        inputs = work / 'inputs'
        self.checkpoint('extracting', 'Extracting and verifying your ROM…')
        extract = load_module('_retuned_prepare_inputs', PROJECT / 'tools/native/prepare_inputs.py')
        extract.prepare(engine, rom, inputs)
        self.checkpoint('normalizing', 'Preparing compatible game resources…')
        adapter = load_module('_retuned_copy_adapter', release / 'input_copy_adapter.py')
        adapter.normalize_file(inputs / 'code.bin', work / 'canonical-code.bin', json.loads(
            (release / 'input_coverage/recipes/adapters/oot3d-usa-ef210566-copies.json').read_text()))
        region = load_module('_retuned_region', release / 'oot3d_region_assets.py')
        region.normalize_romfs(inputs / 'romfs.bin', work / 'romfs.bin')
        if digest(work / 'canonical-code.bin') != CANONICAL_CODE or digest(work / 'romfs.bin') != CANONICAL_ROMFS:
            raise SetupError('The ROM could not be normalized to the supported version.')
        process_tool = load_module('_retuned_process_manifest', a32 / 'build_process_manifest.py')
        write_json(work / 'base-manifest.json', process_tool.build_manifest(
            inputs / 'exheader.bin', work / 'canonical-code.bin', work / 'romfs.bin'))
        inventory_tool = load_module('_retuned_inventory', a32 / 'generate_aot.py')
        inventory_tool.add_local_entry_intervals(a32 / 'upstream/analysis/codebin_function_inventory.csv',
            a32 / 'runtime_discovered_entries.csv', work / 'inventory.csv', 0x100000)
        self.checkpoint('patching', 'Applying the ReTuned HUD and menu integration…')
        image = work / 'image'
        patcher = load_module('_retuned_mod_image', PROJECT / 'tools/reframed/prepare_native_image.py')
        patcher.prepare(argparse.Namespace(code=work / 'canonical-code.bin', ips=self.ips, elf=self.elf,
            inventory=work / 'inventory.csv', manifest=work / 'base-manifest.json', readelf=self.readelf,
            output=image, native_frontend=True, save_context=0x587958))
        self.checkpoint('translating', 'Translating your game locally. This may take several minutes…')
        self.run([sys.executable, a32 / 'whole_aot_program.py', '--code', image / 'code.bin',
            '--inventory', image / 'inventory.csv', '--boundary-audit',
            a32 / 'upstream/analysis/codebin_callable_boundary_residue_audit_166.csv',
            '--observed-sites', image / 'observed-sites.json', '--include-instructions',
            '--executable-size', str(next(s['file_size'] for s in json.loads((image / 'process-manifest.json').read_text())['process']['segments'] if s['name'] == 'text')),
            '--output', work / 'aot-program.json'])
        program = json.loads((work / 'aot-program.json').read_text())
        if any(program['counts'].get(name, 0) for name in ('unclaimed_blocks', 'unresolved_static_edges')):
            raise SetupError('Translation did not cover the complete game; setup was not activated.')
        external = json.loads((a32 / 'whole_aot_functions.json').read_text())['external_functions']
        excluded = {f['entry'] for f in external}
        functions = [f for f in program['functions'] if f['entry'] not in excluded]
        write_json(work / 'selection.json', {'format': 'oot3d_whole_aot_function_selection_v1',
            'selection_mode': 'all_lowerable', 'functions': [{'entry': f['entry'], 'name': f['name'],
            'reason': 'closed ReTuned native translation'} for f in functions],
            'external_functions': external, 'performance_exclusions': [], 'selection_conflicts': [], 'closure_groups': []})
        del program, functions
        gc.collect()
        generated = work / 'title-source'
        self.run([sys.executable, PROJECT / 'tools/native/generate_title_sources.py', '--engine', engine,
            '--program', work / 'aot-program.json',
            '--selection', work / 'selection.json', '--code', image / 'code.bin', '--output', generated,
            '--shards', '64'])
        sources = {p.name: digest(p) for p in generated.iterdir() if p.suffix in ('.cpp', '.h')}
        write_json(generated / 'TITLE_SOURCE_MANIFEST.json', {
            'format': 'triaevum_translated_title_source_v1', 'private_local_artifact': True,
            'redistributable': False, 'files': sources})
        self.checkpoint('compiling', 'Building the native game module…')
        library = self.compile_title(work, generated)
        self.checkpoint('verifying', 'Verifying the native module before activating setup…')
        self.verify_title(library)
        stage = work / 'installation'
        stage.mkdir()
        for source, name in ((work / 'canonical-code.bin', 'canonical-code.bin'), (image / 'code.bin', 'code.bin'), (inputs / 'exheader.bin', 'exheader.bin'),
                             (work / 'romfs.bin', 'romfs.bin'), (library, library.name)):
            shutil.move(source, stage / name)
        installation_id = uuid.uuid4().hex
        final = root / 'installations' / installation_id
        manifest = json.loads((image / 'process-manifest.json').read_text())
        manifest['source'].update(code_bin_path=str(final / 'code.bin'),
            exheader_path=str(final / 'exheader.bin'), romfs_image_path=str(final / 'romfs.bin'))
        write_json(stage / 'process-manifest.json', manifest)
        write_json(stage / 'setup-receipt.json', {'format': 'retuned_local_setup_v1',
            'runtime_revision': RUNTIME_REVISION, 'platform': platform.system(), 'architecture': platform.machine(),
            'private_local_artifact': True, 'redistributable': False,
            'files': {p.name: digest(p) for p in stage.iterdir()}})
        self.checkpoint('activating', 'Finishing setup…')
        target = activate(root, stage, installation_id,
            lambda target: launch_profile(self.profile_root or root, target), profile_root=self.profile_root)
        self.progress({'stage': 'complete', 'message': 'Setup complete. Your game is ready.', 'installation': str(target)})
        return target


    def compile_title(self, work, generated):
        engine = self.engine
        build = work / 'build'
        args = [self.cmake, '-S', PROJECT / 'tools/native/title', '-B', build, '-G', 'Ninja',
            '-DCMAKE_BUILD_TYPE=Release', '-DRETUNED_RUNTIME_SOURCE=' + str(engine),
            '-DTRIAEVUM_TRANSLATED_TITLE_DIR=' + str(generated)]
        if sys.platform == 'darwin':
            args.append('-DCMAKE_OSX_ARCHITECTURES=arm64')
        self.run([*args, *self.cmake_args])
        self.run([self.cmake, '--build', build, '--parallel', str(self.jobs)])
        extension = '.dylib' if sys.platform == 'darwin' else '.dll' if os.name == 'nt' else '.so'
        library = build / ('triaevum_title_aot' + extension)
        return library

    def verify_title(self, library):
        self.run([self.host, '--verify-title-plugin', library])


def launch_profile(root, installation):
    existing = root / 'native-launch.json'
    extension = '.dylib' if sys.platform == 'darwin' else '.dll' if os.name == 'nt' else '.so'
    replacements = {'--a32-process-manifest': str(installation / 'process-manifest.json'),
                    '--title-plugin': str(installation / ('triaevum_title_aot' + extension))}
    if existing.exists():
        previous = json.loads(existing.read_text())
        arguments = previous.get('arguments')
        if previous.get('format') != 'oot3d_native_game_launch_profile_v1' or not isinstance(arguments, list) or not all(isinstance(v, str) for v in arguments):
            raise SetupError('Existing launch settings are invalid; preserving them for recovery.')
        arguments = list(arguments)
        for flag, value in replacements.items():
            if flag in arguments:
                index = arguments.index(flag) + 1
                if index == len(arguments):
                    raise SetupError('Existing launch settings are incomplete; preserving them.')
                arguments[index] = value
            else:
                arguments.extend([flag, value])
        return {**previous, 'arguments': arguments}
    arguments = ['--a32-process-manifest', str(installation / 'process-manifest.json'),
        '--title-plugin', str(installation / ('triaevum_title_aot' + ('.dylib' if sys.platform == 'darwin' else '.dll' if os.name == 'nt' else '.so'))),
        '--resource-root', str(root), '--renderer', 'nri', '--ui-profile', 'reframed',
        '--config', str(root / 'config/native-game.json'), '--controls-config', str(root / 'config/controls.json'),
        '--save-data', str(root / 'saves'), '--renderer-cache-directory', str(root / 'cache'),
        '--gameplay-timing', 'native30_no_interpolation', '--presentation-rate', '30',
        '--width', '1280', '--height', '720', '--output', str(root / 'logs/native-summary.json')]
    return {'format': 'oot3d_native_game_launch_profile_v1', 'arguments': arguments}


def load_kit(path, host=None):
    path = Path(path).resolve()
    kit = json.loads(path.read_text())
    if kit.get('format') != 'retuned_rom_preparation_kit_v1':
        raise SetupError('Unsupported preparation kit')
    def asset(name):
        relative = Path(kit[name])
        if relative.is_absolute() or '..' in relative.parts:
            raise SetupError('Preparation kit path escapes its directory')
        result = (path.parent / relative).resolve()
        if not result.is_relative_to(path.parent):
            raise SetupError('Preparation kit link escapes its directory')
        return result
    cmake_args = list(kit.get('cmake_args', []))
    if 'json_include' in kit:
        cmake_args.append('-DRETUNED_JSON_INCLUDE_DIR=' + str(asset('json_include')))
    tools = {}
    if 'windows_tools' in kit:
        if sys.platform != 'win32':
            raise SetupError('This preparation kit requires Windows.')
        root = asset('windows_tools')
        tools = {'windows_tools': root, 'cmake': root / 'cmake/bin/cmake.exe'}
        cmake_args.append('-DCMAKE_TOOLCHAIN_FILE=' + str(root / 'windows-toolchain.cmake'))
    return {**tools, 'engine': asset('engine'), 'ips': asset('ips'), 'elf': asset('elf'),
        'host': Path(host).resolve() if host is not None else asset('host'),
        'readelf': asset('readelf') if 'readelf' in kit else 'unused',
        'cmake_args': cmake_args}


class FileCancellation:
    def __init__(self, path):
        self.path = Path(path)

    def is_set(self):
        return self.path.exists()

    def wait(self, seconds):
        time.sleep(seconds)
        return self.is_set()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('rom', 'data-root'):
        parser.add_argument('--' + field, type=Path)
    parser.add_argument('--kit', type=Path)
    parser.add_argument('--check-kit', action='store_true', help='Verify local preparation tools without reading a ROM or changing game data')
    for field in ('engine', 'ips', 'elf', 'host'):
        parser.add_argument('--' + field, type=Path)
    parser.add_argument('--readelf', default='arm-none-eabi-readelf')
    parser.add_argument('--cmake-arg', action='append', default=[])
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--progress-file', type=Path)
    parser.add_argument('--cancel-file', type=Path)
    args = parser.parse_args()
    if not args.check_kit and (args.rom is None or args.data_root is None):
        parser.error('--rom and --data-root are required for preparation')
    def progress(value):
        print(json.dumps(value), flush=True)
        if args.progress_file:
            temporary = args.progress_file.with_suffix('.partial')
            write_json(temporary, value)
            os.replace(temporary, args.progress_file)
    try:
        options = load_kit(args.kit, host=args.host) if args.kit else dict(engine=args.engine, ips=args.ips,
            elf=args.elf, host=args.host, readelf=args.readelf, cmake_args=args.cmake_arg)
        if any(options[name] is None for name in ('engine', 'ips', 'elf', 'host')):
            raise SetupError('The local preparation kit is incomplete.')
        setup = RomSetup(**options, jobs=args.jobs, progress=progress,
            cancel=FileCancellation(args.cancel_file) if args.cancel_file else None)
        if args.check_kit:
            setup.preflight()
            progress({'stage': 'checked', 'message': 'Local preparation tools are ready.'})
        else:
            setup.prepare(args.rom, args.data_root)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        progress({'stage': 'error', 'message': str(error)})
        return 1
    return 0


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    raise SystemExit(main())
