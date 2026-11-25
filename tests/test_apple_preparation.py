import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/native'))
spec = importlib.util.spec_from_file_location('apple_preparation', ROOT / 'tools/native/prepare_apple_app.py')
apple = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apple)


class ApplePreparationTests(unittest.TestCase):
    def test_cloud_environment_is_one_authorized_value_not_profile_array(self):
        key = 'com.apple.developer.icloud-container-environment'
        profile = {'Platform': ['tvOS'], 'Entitlements': {
            'application-identifier': 'TEAM.io.example.game',
            'get-task-allow': True, key: ['Production', 'Development']}}
        self.assertEqual(apple.signing_entitlements(profile, 'io.example.game', 'tvos')[key], 'Development')
        self.assertEqual(profile['Entitlements'][key], ['Production', 'Development'])
        profile['Entitlements']['get-task-allow'] = False
        self.assertEqual(apple.signing_entitlements(profile, 'io.example.game', 'tvos')[key], 'Production')
        profile['Entitlements'][key] = 'Development'
        self.assertEqual(apple.signing_entitlements(profile, 'io.example.game', 'tvos')[key], 'Development')
        profile['Entitlements'][key] = []
        with self.assertRaisesRegex(ValueError, 'iCloud environment'):
            apple.signing_entitlements(profile, 'io.example.game', 'tvos')

    def test_profile_cannot_change_platform_or_claim_another_app(self):
        profile = {'Platform': ['iOS'], 'Entitlements': {
            'application-identifier': 'TEAM.io.example.game',
            'keychain-access-groups': ['TEAM.io.example.game'],
            'com.apple.developer.icloud-container-identifiers': ['iCloud.io.example.game']}}
        with self.assertRaisesRegex(ValueError, 'platform'):
            apple.signing_entitlements(profile, 'io.example.game', 'tvos')
        with self.assertRaisesRegex(ValueError, 'identifier'):
            apple.signing_entitlements(profile, 'io.example.other', 'ios')
        entitlements = apple.signing_entitlements(profile, 'io.example.game', 'ios')
        self.assertEqual(entitlements['com.apple.developer.icloud-container-identifiers'],
                         ['iCloud.io.example.game'])
        self.assertEqual(profile['Entitlements']['application-identifier'], 'TEAM.io.example.game')

    def test_wildcard_profile_does_not_invent_cloud_entitlements(self):
        profile = {'Platform': ['tvOS'], 'Entitlements': {
            'application-identifier': 'TEAM.*', 'keychain-access-groups': ['TEAM.*']}}
        result = apple.signing_entitlements(profile, 'io.example.game', 'tvos')
        self.assertEqual(result['application-identifier'], 'TEAM.io.example.game')
        self.assertEqual(result['keychain-access-groups'], ['TEAM.io.example.game'])
        self.assertFalse(any('icloud' in key for key in result))

    def test_cross_target_module_rejects_mac_or_incomplete_exports(self):
        def commands(*args):
            if args[0] == 'lipo':
                return 'arm64\n'
            if args[1] == 'vtool':
                return ' platform MACOS\n'
            return ''
        with patch.object(apple, 'output', side_effect=commands):
            with self.assertRaisesRegex(ValueError, 'wrong Apple platform'):
                apple.check_apple_module(Path('title.dylib'), 'ios')
        with patch.object(apple, 'output', side_effect=['arm64\n', ' platform IOS\n', '_triaevum_title_aot_query\n']):
            with self.assertRaisesRegex(ValueError, 'ABI entry points'):
                apple.check_apple_module(Path('title.dylib'), 'ios')

    def test_private_profile_uses_device_paths_and_separate_writable_saves(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'process-manifest.json').write_text(json.dumps({'source': {
                'code_bin_path': '/private-preparation/code.bin',
                'exheader_path': '/private-preparation/exheader.bin',
                'romfs_image_path': '/private-preparation/romfs.bin'}}))
            manifest, profile = apple.private_documents(root)
            self.assertTrue(all(value.startswith('@BUNDLE@/') for value in manifest['source'].values()))
            arguments = profile['arguments']
            self.assertEqual(arguments[arguments.index('--save-data') + 1], '@DATA@/saves')
            self.assertEqual(arguments[arguments.index('--title-plugin') + 1],
                             '@BUNDLE@/Frameworks/triaevum_title_aot.framework/triaevum_title_aot')
            self.assertNotIn(temporary, json.dumps([manifest, profile]))

    def test_randomizer_fixture_cannot_mix_image_or_seed_and_uses_its_own_save_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            code, seed = b'combined image', b'fixture seed'
            (root / 'code.bin').write_bytes(code)
            (root / 'seed.json').write_bytes(seed)
            (root / 'process-manifest.json').write_text(json.dumps({
                'source': {'code_bin_sha256': hashlib.sha256(code).hexdigest()},
                'randomizer_proof': {'seed_file': 'seed.json', 'seed_layout': {'schema': 1},
                                     'seed_sha256': hashlib.sha256(seed).hexdigest()},
            }))
            _, profile = apple.private_documents(root, randomizer_test=True)
            args = profile['arguments']
            self.assertEqual(args[args.index('--save-data') + 1], '@DATA@/randomizer/bootstrap')
            for path in (root / 'code.bin', root / 'seed.json'):
                with self.subTest(path=path.name):
                    expected = path.read_bytes()
                    path.write_bytes(b'different')
                    with self.assertRaisesRegex(ValueError, 'seed and image must match'):
                        apple.private_documents(root, randomizer_test=True)
                    path.write_bytes(expected)

    def test_combined_package_shares_identical_resources_and_isolates_code_and_seed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            normal, alternate = root / 'PrivateGame', root / 'prepared'
            normal.mkdir()
            alternate.mkdir()
            for name, data in [('exheader.bin', b'header'), ('romfs.bin', b'game resources')]:
                (normal / name).write_bytes(data)
                (alternate / name).write_bytes(data)
            (normal / 'code.bin').write_bytes(b'normal game')
            (alternate / 'code.bin').write_bytes(b'randomized game')
            (alternate / 'seed.json').write_bytes(b'initial seed')
            document = {'source': {'code_bin_sha256': hashlib.sha256(b'randomized game').hexdigest()},
                        'randomizer_proof': {'seed_file': 'seed.json', 'seed_layout': {'schema': 1},
                            'seed_sha256': hashlib.sha256(b'initial seed').hexdigest(), 'activation_allowed': False}}
            (alternate / 'process-manifest.json').write_text(json.dumps(document))
            with self.assertRaisesRegex(ValueError, 'isolated test'):
                apple.stage_randomizer_resources(normal, alternate, 'io.github.otpr26.ocarinaretuned')
            staged = apple.stage_randomizer_resources(normal, alternate, 'io.github.otpr26.ocarinaretuned.randomizer-test')
            self.assertEqual(staged['source']['code_bin_path'], '@BUNDLE@/PrivateGame/Randomizer/code.bin')
            self.assertEqual(staged['source']['romfs_image_path'], '@BUNDLE@/PrivateGame/romfs.bin')
            self.assertEqual({p.name for p in (normal / 'Randomizer').iterdir()},
                             {'code.bin', 'seed.json', 'process-manifest.json'})
            self.assertEqual((normal / 'code.bin').read_bytes(), b'normal game')


if __name__ == '__main__':
    unittest.main()
