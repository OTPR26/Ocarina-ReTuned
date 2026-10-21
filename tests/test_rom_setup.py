import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from types import SimpleNamespace

MODULE = Path(__file__).resolve().parents[1] / 'tools/native/rom_setup.py'
spec = importlib.util.spec_from_file_location('rom_setup', MODULE)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class RomSetupTransactions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'saves').mkdir()
        (self.root / 'saves/save.bin').write_bytes(b'saved progress')
        (self.root / 'config').mkdir()
        (self.root / 'config/controls.json').write_bytes(b'{"custom":true}')
        self.old_profile = json.dumps({'format': 'oot3d_native_game_launch_profile_v1', 'arguments': ['--save-data', str(self.root / 'saves'), '--presentation-rate', '90', '--title-plugin', 'old.so', '--a32-process-manifest', 'old.json']}).encode()
        (self.root / 'native-launch.json').write_bytes(self.old_profile)

    def unchanged(self):
        self.assertEqual((self.root / 'saves/save.bin').read_bytes(), b'saved progress')
        self.assertEqual((self.root / 'config/controls.json').read_bytes(), b'{"custom":true}')

    def test_failure_leaves_existing_profile_and_cleans_partial_data(self):
        with self.assertRaises(RuntimeError):
            with setup.installation_transaction(self.root) as (root, work):
                (work / 'partial').write_bytes(b'partial')
                raise RuntimeError('simulated extraction failure')
        self.assertEqual((self.root / 'native-launch.json').read_bytes(), self.old_profile)
        self.assertFalse(list(self.root.glob('.rom-setup*')))
        self.unchanged()

    def test_simultaneous_setup_is_rejected_without_unlocking_first(self):
        with setup.installation_transaction(self.root):
            with self.assertRaises(setup.SetupError):
                with setup.installation_transaction(self.root):
                    self.fail('second writer admitted')
            self.assertTrue((self.root / '.rom-setup.lock').exists())
        self.unchanged()

    def test_atomic_activation_and_user_preferences_preserved(self):
        with setup.installation_transaction(self.root) as (root, work):
            stage = work / 'stage'
            stage.mkdir()
            (stage / 'verified.dat').write_bytes(b'verified')
            target = setup.activate(root, stage, 'abc123', lambda p: setup.launch_profile(root, p))
            profile = json.loads((root / 'native-launch.json').read_text())
            self.assertTrue((target / 'verified.dat').exists())
            args = profile['arguments']
            self.assertEqual(args[args.index('--save-data') + 1], str(root / 'saves'))
            self.assertIn(str(target / 'process-manifest.json'), args)
            self.assertIn('--title-plugin', args)
            self.assertEqual(args[args.index('--presentation-rate') + 1], '90')
        self.unchanged()

    def test_failed_profile_switch_rolls_back_installation(self):
        with setup.installation_transaction(self.root) as (root, work):
            stage = work / 'stage'
            stage.mkdir()
            with patch.object(setup.os, 'replace', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    setup.activate(root, stage, 'abc123', lambda p: {})
            self.assertTrue(stage.exists())
            self.assertFalse((root / 'installations/abc123').exists())
            self.assertEqual((root / 'native-launch.json').read_bytes(), self.old_profile)
        self.unchanged()

    def test_internal_module_and_separate_userdata_profile(self):
        internal = self.root / 'internal'
        with setup.installation_transaction(internal) as (root, work):
            stage = work / 'stage'
            stage.mkdir()
            (stage / 'module.so').write_bytes(b'local native module')
            target = setup.activate(root, stage, 'separate',
                lambda p: setup.launch_profile(self.root, p), profile_root=self.root)
        profile = json.loads((self.root / 'native-launch.json').read_text())
        self.assertTrue(target.is_relative_to(internal))
        self.assertFalse((internal / 'native-launch.json').exists())
        arguments = profile['arguments']
        self.assertEqual(arguments[arguments.index('--save-data') + 1], str(self.root / 'saves'))
        self.assertIn(str(target / 'process-manifest.json'), arguments)
        self.unchanged()

    def test_refuses_profile_symlink(self):
        (self.root / 'native-launch.json').unlink()
        outside = self.root / 'unrelated.json'
        outside.write_bytes(b'keep')
        (self.root / 'native-launch.json').symlink_to(outside)
        with setup.installation_transaction(self.root) as (root, work):
            stage = work / 'stage'
            stage.mkdir()
            with self.assertRaises(setup.SetupError):
                setup.activate(root, stage, 'abc123', lambda p: {})
        self.assertEqual(outside.read_bytes(), b'keep')

    def test_cancel_before_preflight_does_not_create_installation(self):
        cancel = threading.Event()
        cancel.set()
        worker = setup.RomSetup(engine=self.root, ips='missing', elf='missing', host='missing', cancel=cancel)
        with self.assertRaises(setup.SetupCancelled):
            worker.prepare('missing.3ds', self.root)
        self.assertFalse((self.root / 'installations').exists())
        self.unchanged()


if __name__ == '__main__':
    unittest.main()


class PreparationSourceIntegrity(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'translator.py').write_text('def translate(value): return value\n')
        self.metadata = {'format': 'retuned_preparation_runtime_v1',
            'source_revision': setup.RUNTIME_REVISION,
            'files': {'translator.py': setup.digest(self.root / 'translator.py')}}
        self.save_manifest()

    def save_manifest(self):
        (self.root / 'preparation-runtime.json').write_text(json.dumps(self.metadata))

    def test_minimal_tree_without_git_and_python_caches(self):
        setup.verify_preparation_source(self.root)
        cache = self.root / '__pycache__'
        cache.mkdir()
        (cache / 'translator.cpython.pyc').write_bytes(b'local interpreter cache')
        setup.verify_preparation_source(self.root)

    def test_modified_or_extra_source_is_rejected(self):
        (self.root / 'translator.py').write_text('changed source\n')
        with self.assertRaises(setup.SetupError):
            setup.verify_preparation_source(self.root)
        (self.root / 'translator.py').write_text('def translate(value): return value\n')
        (self.root / 'extra.py').write_text('unexpected source\n')
        with self.assertRaises(setup.SetupError):
            setup.verify_preparation_source(self.root)

    def test_source_paths_cannot_escape_tree(self):
        self.metadata['files'] = {'../outside.py': '0' * 64}
        self.save_manifest()
        with self.assertRaises(setup.SetupError):
            setup.verify_preparation_source(self.root)


class PreparationKitHost(unittest.TestCase):
    def test_running_host_override_needs_no_duplicate_binary_in_kit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            kit = root / 'setup/kit.json'
            kit.parent.mkdir()
            kit.write_text(json.dumps({'format': 'retuned_rom_preparation_kit_v1',
                'engine': 'engine', 'ips': 'hud.ips', 'elf': 'hud.elf'}))
            options = setup.load_kit(kit, host=root / 'app')
            self.assertEqual(options['host'], root / 'app')
            self.assertEqual(options['engine'], root / 'setup/engine')
            self.assertEqual(options['readelf'], 'unused')

    def test_kit_metadata_still_cannot_point_outside_its_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            kit = root / 'kit.json'
            kit.write_text(json.dumps({'format': 'retuned_rom_preparation_kit_v1',
                'engine': '../outside', 'ips': 'hud.ips', 'elf': 'hud.elf'}))
            with self.assertRaises(setup.SetupError):
                setup.load_kit(kit, host=root / 'app')

    def test_bundled_headers_are_resolved_without_machine_specific_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            kit = root / 'kit.json'
            metadata = {'format': 'retuned_rom_preparation_kit_v1', 'engine': 'engine',
                'ips': 'hud.ips', 'elf': 'hud.elf', 'json_include': 'headers'}
            kit.write_text(json.dumps(metadata))
            options = setup.load_kit(kit, host=root / 'app')
            self.assertEqual(options['cmake_args'], ['-DRETUNED_JSON_INCLUDE_DIR=' + str(root / 'headers')])
            metadata['json_include'] = '../outside'
            kit.write_text(json.dumps(metadata))
            with self.assertRaises(setup.SetupError):
                setup.load_kit(kit, host=root / 'app')

class WindowsGuiBuildEnvironment(unittest.TestCase):
    def test_portable_kit_rejects_an_unmatched_host_before_loading_a_game(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ('host.exe', 'hud.ips', 'hud.elf'):
                (root / name).write_bytes(b'fixture')
            (root / 'tools').mkdir()
            (root / 'tools/toolchain-manifest.json').write_text(json.dumps({
                'abi': 'x86_64-llvm-mingw-ucrt-20261006'}))
            instance = setup.RomSetup(engine=root, ips=root / 'hud.ips', elf=root / 'hud.elf',
                host=root / 'host.exe', windows_tools=root / 'tools')
            with patch.object(setup, 'verify_preparation_source'):
                with self.assertRaisesRegex(setup.SetupError, 'do not match'):
                    instance.preflight()
                (root / 'preparation-abi.json').write_text(json.dumps({
                    'abi': 'x86_64-llvm-mingw-ucrt-20261006', 'host_sha256': 'incorrect'}))
                with self.assertRaisesRegex(setup.SetupError, 'do not match'):
                    instance.preflight()

    def test_portable_tools_ignore_installed_sdk_and_do_not_change_parent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ('llvm/bin/x86_64-w64-mingw32-clang++.exe', 'cmake/bin/cmake.exe', 'ninja/ninja.exe'):
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(b'tool fixture')
            original = {'PATH': 'untrusted-sdk-path', 'INCLUDE': 'installed-vs', 'LIB': 'installed-vs',
                        'CXX': 'cl.exe', 'SYSTEMROOT': r'C:\Windows', 'TEMP': 'keep-me'}
            saved = dict(original)
            result = setup.portable_windows_environment(original, root)
            self.assertEqual(original, saved)
            self.assertNotIn('untrusted-sdk-path', result['PATH'])
            self.assertNotIn('INCLUDE', result)
            self.assertNotIn('LIB', result)
            self.assertNotIn('CXX', result)
            self.assertEqual(result['TEMP'], 'keep-me')
            self.assertIn(str(root / 'llvm/bin'), result['PATH'])
            (root / 'ninja/ninja.exe').unlink()
            with self.assertRaises(setup.SetupError):
                setup.portable_windows_environment(original, root)

    def test_portable_kit_resolves_compiler_tools_within_kit_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            kit = root / 'kit.json'
            metadata = {'format': 'retuned_rom_preparation_kit_v1', 'engine': 'engine',
                        'ips': 'hud.ips', 'elf': 'hud.elf', 'windows_tools': 'tools'}
            kit.write_text(json.dumps(metadata))
            with patch.object(setup.sys, 'platform', 'win32'):
                options = setup.load_kit(kit, host=root / 'app.exe')
                self.assertEqual(options['cmake'], root / 'tools/cmake/bin/cmake.exe')
                self.assertEqual(options['windows_tools'], root / 'tools')
                self.assertIn('-DCMAKE_TOOLCHAIN_FILE=' + str(root / 'tools/windows-toolchain.cmake'), options['cmake_args'])
                metadata['windows_tools'] = '../outside'
                kit.write_text(json.dumps(metadata))
                with self.assertRaises(setup.SetupError):
                    setup.load_kit(kit, host=root / 'app.exe')

    def test_gui_launch_discovers_buildtools_and_preserves_parent_environment(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            installer = root / 'Microsoft Visual Studio/Installer/vswhere.exe'
            installation = root / 'Build Tools & SDK'
            vcvars = installation / 'VC/Auxiliary/Build/vcvars64.bat'
            cmake = installation / 'Common7/IDE/CommonExtensions/Microsoft/CMake'
            for file in (installer, vcvars, cmake / 'CMake/bin/cmake.exe', cmake / 'Ninja/ninja.exe'):
                file.parent.mkdir(parents=True, exist_ok=True)
                file.touch()
            original = {'ProgramFiles(x86)': str(root), 'PATH': 'existing', 'CUSTOM': 'preserved'}
            outputs = [SimpleNamespace(stdout=str(installation) + '\n'),
                SimpleNamespace(stdout='Path=compiler-tools\nINCLUDE=sdk-headers\nVSCMD_ARG_TGT_ARCH=x64\n=value\n')]
            with patch.object(setup.subprocess, 'run', side_effect=outputs) as run:
                result = setup.windows_build_environment(original)
            self.assertEqual(original['PATH'], 'existing')
            self.assertEqual(result['CUSTOM'], 'preserved')
            self.assertEqual(result['INCLUDE'], 'sdk-headers')
            self.assertTrue(result['PATH'].startswith('compiler-tools;'))
            self.assertIn(str(cmake / 'Ninja'), result['PATH'])
            call = run.call_args_list[1]
            self.assertEqual(call.kwargs['env']['RETUNED_VCVARS'], str(vcvars))
            self.assertTrue(call.args[0].endswith(' /c call "%RETUNED_VCVARS%" >nul && set'))
            self.assertNotIn('\\"', call.args[0])
            self.assertNotIn('RETUNED_VCVARS', result)

    def test_missing_tools_make_no_machine_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            environment = {'PROGRAMFILES(X86)': temporary, 'PATH': 'existing'}
            with patch.object(setup.subprocess, 'run') as run:
                self.assertEqual(setup.windows_build_environment(environment), environment)
            run.assert_not_called()
