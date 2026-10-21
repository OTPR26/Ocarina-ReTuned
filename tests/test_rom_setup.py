import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

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
