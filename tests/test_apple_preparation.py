import importlib.util
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


if __name__ == '__main__':
    unittest.main()
