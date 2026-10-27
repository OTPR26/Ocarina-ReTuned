#!/usr/bin/env python3
"""Local ROM-to-native preparation. Generated files never leave this machine.

The preparation kit contains translation tools and our HUD mod; it must match
this application's tested revision. No prepared title is downloaded. Desktop
Windows packages include their compiler and build tools. Other desktop kits
may require the platform tools described in their setup instructions.
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
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preparation_cache import LocalCache, fingerprint

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


WINDOWS_COMPILER_TARGETS = {
    'x86_64-llvm-mingw-ucrt-20261006': 'x86_64',
    'aarch64-llvm-mingw-ucrt-20261006': 'aarch64',
}


def portable_windows_environment(environment, tools):
    """Use only the app's compiler/build tools and Windows system executables."""
    root = Path(tools).resolve()
    result = {name.upper(): value for name, value in environment.items()}
    for name in ('INCLUDE', 'LIB', 'LIBPATH', 'CC', 'CXX', 'CFLAGS', 'CXXFLAGS',
                 'LDFLAGS', 'CMAKE_TOOLCHAIN_FILE', 'VCTOOLSINSTALLDIR', 'VCINSTALLDIR',
                 'VSINSTALLDIR', 'WINDOWSSDKDIR', 'VSCMD_ARG_TGT_ARCH'):
        result.pop(name, None)
    directories = [root / 'llvm/bin', root / 'cmake/bin', root / 'ninja']
    try:
        metadata = json.loads((root / 'toolchain-manifest.json').read_text())
        target = WINDOWS_COMPILER_TARGETS[metadata['abi']]
    except (OSError, ValueError, KeyError) as error:
        raise SetupError('The bundled Windows compiler manifest is missing or unsupported.') from error
    for executable in (directories[0] / (target + '-w64-mingw32-clang++.exe'),
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
        # Windows _commit requires a writable descriptor. Read-only fsync works
        # on Unix but fails with EBADF after otherwise successful preparation.
        with temporary_profile.open('r+b') as stream:
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
                 windows_tools=None, ui_resources=None, hd_font_coverage=None, dialogue_font=None, preparation_identity=None):
        if preparation_identity is not None and (len(preparation_identity) != 64 or any(c not in "0123456789abcdef" for c in preparation_identity)):
            raise SetupError("Invalid preparation identity")
        self.preparation_identity = preparation_identity
        self.engine = Path(engine).resolve()
        self.ips, self.elf, self.host = map(lambda p: Path(p).resolve(), (ips, elf, host))
        self.ui_resources = Path(ui_resources).resolve() if ui_resources is not None else self.ips.with_name('native-ui.zip')
        self.hd_font_coverage = Path(hd_font_coverage).resolve() if hd_font_coverage is not None else None
        self.dialogue_font = Path(dialogue_font).resolve() if dialogue_font is not None else PROJECT / 'resources/fonts/ReTunedDialogue.qbf'
        self.bundled_dialogue_styles = dialogue_font is None
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
        if not (PROJECT / 'tools/native/prepare_ui_assets.py').is_file():
            raise SetupError('The preparation toolkit lacks native UI asset support. Install the matching toolkit update.')
        for path in (self.ips, self.elf, self.host):
            if not path.is_file():
                raise SetupError('The local preparation kit is incomplete.')
        verify_preparation_source(self.engine)
        if self.windows_tools is not None:
            try:
                compiler = json.loads((self.windows_tools / 'toolchain-manifest.json').read_text())
                host = json.loads(self.host.with_name('preparation-abi.json').read_text())
                if (compiler['abi'] not in WINDOWS_COMPILER_TARGETS or
                        host['abi'] != compiler['abi'] or host['host_sha256'] != digest(self.host)):
                    raise ValueError('Compiler ABI mismatch')
            except (OSError, ValueError, KeyError) as error:
                raise SetupError('The bundled preparation tools do not match this Windows app.') from error
        try:
            assets = load_module('_retuned_ui_preflight', PROJECT / 'tools/native/prepare_ui_assets.py')
            assets.read_pack(self.ui_resources)
            if self.hd_font_coverage is not None:
                assets.verify_font_coverage(self.hd_font_coverage)
            else:
                open_font = load_module('_retuned_open_font_preflight', PROJECT / 'tools/native/prepare_open_font.py')
                if self.bundled_dialogue_styles:
                    open_font.read_styles(PROJECT / 'resources/fonts')
                else:
                    open_font.parse(self.dialogue_font.read_bytes())
                (PROJECT / 'resources/fonts/LICENSE.txt').read_bytes()
        except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
            raise SetupError('The bundled HUD/font resources are missing or damaged. Install the complete matching app package.') from error
        try:
            import capstone
        except ImportError as error:
            raise SetupError('The preparation runtime is missing its Capstone dependency.') from error
        self.verify_host()
        for tool in (self.cmake, 'ninja'):
            if shutil.which(tool, path=self.environment.get('PATH')) is None:
                raise SetupError('Required local build tool is missing: ' + Path(tool).name)

    def verify_host(self):
        subprocess.run([str(self.host), '--product-info'], check=True, env=self.environment,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def prepare(self, rom, data_root):
        self.checkpoint('checking', 'Checking the ROM and local preparation tools…')
        self.preflight()
        rom = Path(rom).expanduser().resolve() if rom is not None else None
        if rom is not None and not rom.is_file():
            raise SetupError('Choose a decrypted Ocarina of Time 3D USA cartridge dump (.3ds or .cci).')
        with installation_transaction(data_root) as (root, work):
            self.cache = LocalCache(root / 'preparation-cache', limit=768 * 1024 * 1024)
            self.input_cache = LocalCache(root / 'verified-inputs', limit=512 * 1024 * 1024)
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
        input_pins = json.loads((PROJECT / 'resources/native-inputs.json').read_text())
        input_key = fingerprint({'format': 'verified-inputs-v1', 'code': CANONICAL_CODE,
                                 'romfs': CANONICAL_ROMFS, 'pins': input_pins})
        expected_inputs = {'canonical-code.bin': CANONICAL_CODE, 'romfs.bin': CANONICAL_ROMFS,
                           'inputs/exheader.bin': input_pins['inputs'][0]['exheader']['sha256']}
        if rom is None:
            self.checkpoint('extracting', 'Checking the verified game inputs already on this device…')
            if not self.input_cache.restore(input_key, work, expected_inputs):
                raise SetupError('Verified game inputs are unavailable or damaged. Choose your ROM once to refresh them; your existing game and saves are unchanged.')
        else:
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
            self.input_cache.store(input_key, {name: work / name for name in expected_inputs})
        self.checkpoint('assets', 'Installing the bundled HUD and menu resources…')
        ui_assets = load_module('_retuned_ui_assets', PROJECT / 'tools/native/prepare_ui_assets.py')
        asset_receipt = ui_assets.prepare(work / 'romfs.bin', work / 'native-romfs.bin',
            resources=self.ui_resources, notices_directory=work / 'ui-notices')
        (work / 'native-romfs.bin').replace(work / 'romfs.bin')
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
        generated = work / 'title-source'
        translation_inputs = {p.relative_to(a32).as_posix(): digest(p) for p in a32.rglob('*')
            if p.is_file() and p.suffix in ('.py', '.json', '.csv') and '__pycache__' not in p.parts}
        source_key = fingerprint({'format': 'retuned-title-sources-v1', 'runtime': RUNTIME_REVISION,
            'tools': translation_inputs, 'generator': digest(PROJECT / 'tools/native/generate_title_sources.py'),
            'shards': getattr(self, 'title_shards', 64), 'strategy': getattr(self, 'title_shard_strategy', 'stable'),
            'image': {name: digest(image / name) for name in ('code.bin', 'inventory.csv', 'observed-sites.json')}})
        if self.cache.restore(source_key, generated):
            self.checkpoint('generating', 'Reusing verified native game code from this device…')
        else:
            if generated.exists():
                shutil.rmtree(generated)
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
            self.run([sys.executable, PROJECT / 'tools/native/generate_title_sources.py', '--engine', engine,
                '--program', work / 'aot-program.json',
                '--selection', work / 'selection.json', '--code', image / 'code.bin', '--output', generated,
                '--observed-sites', image / 'observed-sites.json',
                '--shards', str(getattr(self, 'title_shards', 64)),
                '--shard-strategy', getattr(self, 'title_shard_strategy', 'stable')])
            self.cache.store(source_key, {p.name: p for p in generated.iterdir() if p.suffix in ('.cpp', '.h')})
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
        equipment_art = load_module('_retuned_equipment_art', PROJECT / 'tools/native/prepare_lower_equipment_art.py')
        asset_receipt['lower_equipment'] = equipment_art.prepare_romfs(
            stage / 'romfs.bin', stage / 'lower-equipment')
        shutil.move(work / 'ui-notices', stage / 'ui-notices')
        if self.hd_font_coverage is not None:
            asset_receipt['hd_font_coverage'] = ui_assets.verify_font_coverage(self.hd_font_coverage)
            shutil.copyfile(self.hd_font_coverage, stage / 'font_coverage.zip')
        else:
            open_font = load_module('_retuned_open_font', PROJECT / 'tools/native/prepare_open_font.py')
            native_font = ui_assets.RomFs(stage / 'romfs.bin').read('message/eu/ltn16.qbf')
            if self.bundled_dialogue_styles:
                font_manifest = open_font.pair_styles(native_font, PROJECT / 'resources/fonts', stage / 'font_coverage.zip')
            else:
                font_manifest = open_font.pair(native_font, self.dialogue_font.read_bytes(),
                    stage / 'font_coverage.zip', PROJECT / 'resources/fonts/LICENSE.txt')
            asset_receipt['dialogue_font'] = {'name': font_manifest['name'], 'license': 'OFL-1.1',
                'source_sha256': digest(PROJECT / 'resources/fonts/ReTunedDialogue-Styles.json'
                    if self.bundled_dialogue_styles else self.dialogue_font),
                'styles': ['regular','bold'] if self.bundled_dialogue_styles else ['custom'],
                'pack_sha256': digest(stage / 'font_coverage.zip')}
        write_json(stage / 'ui-assets-receipt.json', asset_receipt)
        write_json(stage / 'setup-receipt.json', {'format': 'retuned_local_setup_v1',
            'preparation_identity': self.preparation_identity,
            'runtime_revision': RUNTIME_REVISION, 'platform': platform.system(), 'architecture': platform.machine(),
            'private_local_artifact': True, 'redistributable': False,
            'files': {p.relative_to(stage).as_posix(): digest(p) for p in stage.rglob('*') if p.is_file()}})
        self.checkpoint('activating', 'Finishing setup…')
        target = activate(root, stage, installation_id,
            lambda target: launch_profile(self.profile_root or root, target), profile_root=self.profile_root)
        self.progress({'stage': 'complete', 'message': 'Setup complete. Your game is ready.', 'installation': str(target)})
        return target


    def compile_title(self, work, generated):
        engine = self.engine
        build = work / 'build'
        self.module_cache_key = None
        cache = getattr(self, 'cache', None)
        if cache is not None:
            compiler = self.environment.get('CXX', 'cl' if os.name == 'nt' and self.windows_tools is None else 'c++')
            if self.windows_tools is not None:
                manifest = json.loads((self.windows_tools / 'toolchain-manifest.json').read_text())
                target = WINDOWS_COMPILER_TARGETS[manifest['abi']]
                compiler = str(self.windows_tools / 'llvm/bin' / (target + '-w64-mingw32-clang++.exe'))
            for argument in self.cmake_args:
                name, _, value = argument.partition('=')
                if name.split(':')[0] == '-DCMAKE_CXX_COMPILER':
                    compiler = value
            executable = shutil.which(compiler, path=self.environment.get('PATH'))
            sources = {}
            for directory in (engine / 'tools/oot3d/native_game_runtime', engine / 'tools/oot3d/native_a32_runtime'):
                for path in directory.rglob('*'):
                    if path.is_file() and path.suffix in ('.h', '.hpp', '.cpp', '.inc') :
                        sources[path.relative_to(engine).as_posix()] = digest(path)
            try:
                version = subprocess.check_output([compiler, '--version'], env=self.environment,
                    stderr=subprocess.STDOUT, timeout=15).decode(errors='replace')
            except (OSError, subprocess.SubprocessError):
                version = None
            sdk_version = None
            if sys.platform == 'darwin':
                try:
                    sdk_version = subprocess.check_output(['xcrun', '--show-sdk-version'],
                        env=self.environment, timeout=15).decode().strip()
                except (OSError, subprocess.SubprocessError):
                    version = None
            for argument in self.cmake_args:
                if argument.startswith('-DRETUNED_JSON_INCLUDE_DIR='):
                    directory = Path(argument.split('=', 1)[1])
                    sources.update({'json/' + p.relative_to(directory).as_posix(): digest(p)
                        for p in directory.rglob('*.hpp') if p.is_file()})
            for path in (engine / 'tools/triaevum_release/cmake').glob('*.cmake'):
                sources[path.relative_to(engine).as_posix()] = digest(path)
            self.module_cache_key = fingerprint({'format': 'retuned-desktop-module-v1',
                'compiler_version': version, 'sdk_version': sdk_version,
                'platform': platform.system(), 'machine': platform.machine(),
                'compiler': digest(executable) if executable else compiler,
                'windows_tools': digest(self.windows_tools / 'toolchain-manifest.json') if self.windows_tools else None,
                'environment': {name: self.environment.get(name) for name in
                    ('CXX', 'CC', 'CXXFLAGS', 'LDFLAGS', 'SDKROOT', 'MACOSX_DEPLOYMENT_TARGET')},
                'cmake_args': self.cmake_args, 'runtime_sources': sources,
                'cmake': digest(PROJECT / 'tools/native/title/CMakeLists.txt'),
                'generated': {p.name: digest(p) for p in generated.iterdir() if p.suffix in ('.cpp', '.h')}})
            extension = '.dylib' if sys.platform == 'darwin' else '.dll' if os.name == 'nt' else '.so'
            library = build / ('triaevum_title_aot' + extension)
            if version is None or not any(a.startswith('-DRETUNED_JSON_INCLUDE_DIR=') for a in self.cmake_args):
                self.module_cache_key = None
            if self.module_cache_key is not None and cache.restore(self.module_cache_key, build, required={library.name}):
                self.checkpoint('compiling', 'Reusing the verified native game module on this device…')
                return library
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
        if getattr(self, 'module_cache_key', None) is not None:
            self.cache.store(self.module_cache_key, {library.name: library})


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
    optional = {name: asset(name) for name in ('ui_resources', 'hd_font_coverage', 'dialogue_font') if name in kit}
    if kit.get('preparation_identity') is not None:
        optional['preparation_identity'] = kit['preparation_identity']
    return {**tools, **optional, 'engine': asset('engine'), 'ips': asset('ips'), 'elf': asset('elf'),
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
    parser.add_argument('--reuse-inputs', action='store_true', help='Update using previously verified local game inputs without selecting a ROM')
    parser.add_argument('--check-kit', action='store_true', help='Verify local preparation tools without reading a ROM or changing game data')
    for field in ('engine', 'ips', 'elf', 'host'):
        parser.add_argument('--' + field, type=Path)
    parser.add_argument('--readelf', default='arm-none-eabi-readelf')
    parser.add_argument('--cmake-arg', action='append', default=[])
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--progress-file', type=Path)
    parser.add_argument('--cancel-file', type=Path)
    args = parser.parse_args()
    if not args.check_kit and (args.data_root is None or (args.rom is None and not args.reuse_inputs)):
        parser.error('--data-root and either --rom or --reuse-inputs are required')
    if args.rom is not None and args.reuse_inputs:
        parser.error('Choose either --rom or --reuse-inputs')
    started = time.time()
    stage_started = started
    active_stage = None
    timing_path = args.data_root / 'preparation-times.json' if args.data_root else None
    try:
        durations = json.loads(timing_path.read_text()) if timing_path else {}
    except (OSError, ValueError):
        durations = {}
    def progress(value):
        nonlocal stage_started, active_stage
        now = time.time()
        stage = value.get('stage')
        if stage != active_stage:
            if active_stage and stage not in ('error', 'cancelled'):
                durations[active_stage] = round((now - stage_started) * 1000)
            stage_started, active_stage = now, stage
        value = dict(value, started_at=round(started*1000), updated_at=round(now*1000),
                     stage_started_at=round(stage_started*1000), previous_duration=durations.get(stage, -1))
        if stage == 'complete' and timing_path:
            try:
                write_json(timing_path, durations)
            except OSError:
                pass
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
