"""Preparation upgrades follow relevant content, not version labels or ZIP timestamps."""
from pathlib import Path
import hashlib
import sys
import tempfile
import json
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/native'))
from preparation_identity import archive_identity, stamp_android, stamp_desktop, NATIVE_TOOLS


class PreparationIdentityTests(unittest.TestCase):
    def test_android_stamp_refreshes_size_and_checksum_after_archive_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in NATIVE_TOOLS:
                (root / name).write_bytes(b'compiler fixture')
            manifest = root / 'preparation-kit.json'
            manifest.write_text(json.dumps({'format': 'retuned_preparation_asset_v1',
                                            'sha256': 'old', 'unpacked_bytes': 1}))
            bundle = root / 'preparation-kit.zip'
            with zipfile.ZipFile(bundle, 'w') as archive:
                archive.writestr('tool.py', b'original')
            first = stamp_android(root, root, root)
            with zipfile.ZipFile(bundle, 'a') as archive:
                archive.writestr('updated.py', b'new tools')
            self.assertNotEqual(first, stamp_android(root, root, root))
            metadata = json.loads(manifest.read_text())
            self.assertEqual(metadata['unpacked_bytes'], 17)
            self.assertEqual(metadata['sha256'], hashlib.sha256(bundle.read_bytes()).hexdigest())

    def test_repacked_inputs_match_but_game_and_compiler_changes_invalidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = {}
            for name in NATIVE_TOOLS:
                tools[name] = root / name
                tools[name].write_bytes(b'compiler')
            def bundle(name, patch=b'patch', order=False):
                path = root / name
                files = [('hud.ips', patch), ('sdk/sdk.json', b'{"ABI":1}')]
                with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                    for key, value in reversed(files) if order else files:
                        archive.writestr(key, value)
                return path
            first = archive_identity(bundle('first.zip'), tools)
            self.assertEqual(first, archive_identity(bundle('repacked.zip', order=True), tools))
            self.assertNotEqual(first, archive_identity(bundle('patch.zip', patch=b'new patch'), tools))
            repacked = bundle('interface.zip')
            with zipfile.ZipFile(repacked, 'a') as archive:
                archive.writestr('project/resources/fonts/interface/body.ttf', b'new menu font')
                archive.writestr('project/tools/native/android/Menu.java', b'new menu layout')
            self.assertEqual(first, archive_identity(repacked, tools))
            # APK interface/version changes are deliberately outside this input set.
            (root / 'interface.ttf').write_bytes(b'new interface font')
            self.assertEqual(first, archive_identity(root / 'first.zip', tools))
            tools[NATIVE_TOOLS[0]].write_bytes(b'new compiler')
            self.assertNotEqual(first, archive_identity(root / 'first.zip', tools))

    def test_duplicate_or_escaping_inputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'bad.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('../hud.ips', b'patch')
            with self.assertRaises(ValueError):
                archive_identity(path, {})

    def test_desktop_ignores_interface_and_version_but_tracks_build_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ('engine/abi.h', 'project/tools/native/rom_setup.py',
                         'project/tools/reframed/patch.py', 'hud.ips', 'hud.elf'):
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('fixture')
            metadata = {'format':'retuned_rom_preparation_kit_v1', 'engine':'engine',
                        'script':'project/tools/native/rom_setup.py', 'ips':'hud.ips', 'elf':'hud.elf'}
            kit = root / 'kit.json'; kit.write_text(json.dumps(metadata))
            first = stamp_desktop(kit)
            frontend = root / 'project/tools/frontend/menu.cpp'
            frontend.parent.mkdir(parents=True); frontend.write_text('new menu')
            font = root / 'project/resources/fonts/interface/body.ttf'
            font.parent.mkdir(parents=True); font.write_text('new interface font')
            metadata = json.loads(kit.read_text()); metadata['version'] = 'new app version'
            kit.write_text(json.dumps(metadata))
            self.assertEqual(first, stamp_desktop(kit))
            (root / 'engine/abi.h').write_text('new ABI')
            changed = stamp_desktop(kit)
            self.assertNotEqual(first, changed)
            metadata = json.loads(kit.read_text()); metadata['cmake_args'] = ['-DNEW_BUILD_OPTION=ON']
            kit.write_text(json.dumps(metadata))
            self.assertNotEqual(changed, stamp_desktop(kit))
