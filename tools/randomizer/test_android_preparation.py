import tempfile
import unittest
from pathlib import Path
from prepare_run import title_target, compile_module, prepare
from unittest.mock import Mock


class AndroidPreparationTests(unittest.TestCase):
    def test_android_requires_ndk_and_uses_android_abi(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            config={'target':'android-arm64','ndk':str(root),'json_headers':str(root/'headers')}
            with self.assertRaises(ValueError):title_target(config)
            toolchain=root/'build/cmake/android.toolchain.cmake'
            toolchain.parent.mkdir(parents=True);toolchain.write_text('# fixture')
            flags,name=title_target(config)
            self.assertEqual(name,'triaevum_title_aot.so')
            self.assertIn('-DANDROID_ABI=arm64-v8a',flags)
            self.assertIn('-DANDROID_STL=c++_shared',flags)
            self.assertFalse(any('OSX' in flag for flag in flags))

    def test_device_compilation_uses_existing_backend_without_desktop_tools(self):
        setup, run = Mock(), Mock()
        setup.compile_title.return_value = Path('/private/module.so')
        result = compile_module({'target': 'android-arm64'}, Path('/work'), Path('/generated'), run, setup)
        self.assertEqual(result, Path('/private/module.so'))
        self.assertEqual([call[0] for call in setup.mock_calls],
                         ['compile_title', 'verify_title'])
        setup.compile_title.assert_called_once_with(Path('/work'), Path('/generated'))
        setup.verify_title.assert_called_once_with(result)
        run.assert_not_called()

    def test_device_integrity_failure_never_compiles(self):
        setup = Mock()
        setup.engine = Path('/engine')
        setup.preflight.side_effect = ValueError('SDK integrity')
        with self.assertRaisesRegex(ValueError, 'SDK integrity'):
            prepare({'target': 'android-arm64', 'engine': '/engine'},
                    Path('/seed.json'), android_setup=setup)
        setup.compile_title.assert_not_called()
        setup.run.assert_not_called()

    def test_invalid_device_module_is_not_returned(self):
        setup = Mock()
        setup.verify_title.side_effect = ValueError('ABI mismatch')
        with self.assertRaisesRegex(ValueError, 'ABI mismatch'):
            compile_module({'target': 'android-arm64'}, Path('/work'), Path('/generated'), Mock(), setup)

    def test_device_backend_rejects_other_platforms(self):
        setup = Mock()
        with self.assertRaises(ValueError):
            compile_module({'target': 'mac-arm64'}, Path('/work'), Path('/generated'), Mock(), setup)
        self.assertEqual(setup.mock_calls, [])

    def test_desktop_default_is_unchanged(self):
        flags,name=title_target({})
        self.assertEqual(flags,['-DCMAKE_OSX_ARCHITECTURES=arm64'])
        self.assertEqual(name,'triaevum_title_aot.dylib')
        with self.assertRaises(ValueError):title_target({'target':'unknown'})


if __name__=='__main__':unittest.main()
