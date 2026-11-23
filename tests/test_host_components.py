"""Hosted artifacts must never contain game data, credentials, or build paths."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('host_archive', ROOT / 'tools/ci/archive_host_components.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class HostComponents(unittest.TestCase):
    def test_private_files_and_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, data in [('save.sav', b'data'), ('key.p12', b'data'),
                               ('PrivateGame/code.bin', b'data'),
                               ('runtime', b'path=/Users/example/project')]:
                with self.subTest(name=name):
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                    with self.assertRaises(ValueError):
                        module.check_file(path, root)

    def test_symlink_cannot_escape_artifact_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'runtime').symlink_to('/etc/hosts')
            with self.assertRaises(ValueError):
                module.check_file(root / 'runtime', root)

    def test_neutral_component_has_verifiable_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'runtime').write_bytes(b'neutral runtime')
            record = module.check_file(root / 'runtime', root)
            self.assertEqual(record['bytes'], 15)
            self.assertEqual(len(record['sha256']), 64)


class AppleFrameworkSelection(unittest.TestCase):
    def test_device_slice_can_contain_multiple_architectures(self):
        import plistlib
        spec = importlib.util.spec_from_file_location('host_build', ROOT / 'tools/ci/build_remaining_hosts.py')
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        with tempfile.TemporaryDirectory() as temp:
            vendor = Path(temp)
            framework = vendor / 'dynamic/MoltenVK.xcframework'
            device = framework / 'tvos-arm64_arm64e/MoltenVK.framework'
            device.mkdir(parents=True)
            data = {'AvailableLibraries': [
                {'LibraryIdentifier': 'tvos-arm64_arm64e', 'LibraryPath': 'MoltenVK.framework',
                 'SupportedPlatform': 'tvos', 'SupportedArchitectures': ['arm64', 'arm64e']},
                {'LibraryIdentifier': 'tvos-arm64-simulator', 'LibraryPath': 'MoltenVK.framework',
                 'SupportedPlatform': 'tvos', 'SupportedArchitectures': ['arm64'],
                 'SupportedPlatformVariant': 'simulator'}]}
            (framework / 'Info.plist').write_bytes(plistlib.dumps(data))
            self.assertEqual(build.moltenvk_framework(vendor, 'tvos'), device.resolve())
            with self.assertRaises(ValueError):
                build.moltenvk_framework(vendor, 'ios')


class SwitchDependencySelection(unittest.TestCase):
    def test_required_lookup_uses_fetched_target_when_sdk_module_is_incomplete(self):
        import shutil
        import subprocess
        if not shutil.which('cmake'):
            self.skipTest('CMake is required for dependency resolution')
        spec = importlib.util.spec_from_file_location('host_build', ROOT / 'tools/ci/build_remaining_hosts.py')
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            deps = root / 'runtime/three_ds_recomp/cmake/dependencies'
            deps.mkdir(parents=True)
            (deps / 'switch.cmake').write_text(
                'include(FetchContent)\nfind_package(tinyxml2 QUIET)\nif(NOT tinyxml2_FOUND)\n'
                'FetchContent_Declare(tinyxml2 SOURCE_DIR "${CMAKE_SOURCE_DIR}/xml" OVERRIDE_FIND_PACKAGE)\n'
                'FetchContent_MakeAvailable(tinyxml2)\nendif()\n')
            (root / 'xml').mkdir()
            (root / 'xml/CMakeLists.txt').write_text(
                'add_library(tinyxml2 INTERFACE)\nadd_library(tinyxml2::tinyxml2 ALIAS tinyxml2)\n')
            (root / 'Findtinyxml2.cmake').write_text('set(tinyxml2_FOUND TRUE)\n')
            (root / 'CMakeLists.txt').write_text(
                'cmake_minimum_required(VERSION 3.24)\nproject(XmlProbe NONE)\n'
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}")\n'
                'include(runtime/three_ds_recomp/cmake/dependencies/switch.cmake)\n'
                'find_package(tinyxml2 REQUIRED)\n'
                'if(NOT TARGET tinyxml2::tinyxml2)\nmessage(FATAL_ERROR "Missing XML target")\nendif()\n')
            build.switch_xml_dependency(root)
            build.switch_xml_dependency(root)
            result = subprocess.run(['cmake', '-S', str(root), '-B', str(root / 'build')],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
