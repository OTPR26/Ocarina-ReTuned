"""Keep startup instrumentation safe to apply to clean and previously staged engines."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('android_startup_staging', ROOT / 'tools/native/apply_android_startup.py')
staging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(staging)


class AndroidStartupStagingTests(unittest.TestCase):
    def test_clean_and_legacy_staging_are_idempotent(self):
        for legacy in (False, True):
            with self.subTest(legacy=legacy), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                native = 'tools/oot3d/native_game_runtime/'
                backend = 'runtime/three_ds_recomp/src/fast/backends/'
                files = {
                    native + 'oot3d_native_game.cpp': (
                        '        InitializeAndroidGameHost();\n'
                        '        if (!Oot3dNativeGame::Oot3dWholeAotPluginV2Available()) {\n'
                        '    } catch (const std::exception& ex) {\n'),
                    native + 'oot3d_native_a32_window_setup.cpp': (
                        'void NativeA32WindowSession::Setup() {\n'
                        '  manifest = Oot3dNativeGame::LoadNativeA32ProcessImageManifest(\n'
                        '  {\n    const auto fontPath =\n'
                        '  auto &process = processStorage.emplace(\n'
                        '  if (!Oot3dNativeGame::MountNativeA32ProcessImage(\n'
                        '          process, *manifest, std::filesystem::path{}, &error)) {\n'
                        '    throw std::runtime_error(error);\n  }\n'
                        '  InitContextForDemo(hostArgs);\n  programPreparation =\n'
                        '    processResult =\n        RunUntilGuestWait(process, launch.WholeAotBlockBudget);\n'),
                    backend + 'gfx_vulkan_lifecycle.cpp': ''.join(
                        '    ' + name + '();\n' for name in ('CreateInstance', 'CreateSurface',
                        'PickPhysicalDevice', 'CreateLogicalDevice', 'CreatePipelineCache',
                        'CreateCommandResources', 'CreateSwapchainResources')),
                    backend + 'gfx_vulkan_device.cpp': (
                        '        Oot3d::VulkanAdapterClass adapterClass =\n'
                        "    // Release logs keep warnings only; the device is what a tester's report\n"),
                    native + 'oot3d_native_a32_window_frame.cpp': 'bool NativeA32WindowSession::RunFrame() {\n',
                }
                if legacy:
                    files[native + 'oot3d_native_game.cpp'] += '        RetunedStartupStage(14);\n'
                    files[backend + 'gfx_vulkan_lifecycle.cpp'] = files[backend + 'gfx_vulkan_lifecycle.cpp'].replace(
                        '    CreateInstance();', '    RetunedStartupStage(8);\n    CreateInstance();')
                for name, text in files.items():
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(text)
                (root / 'runtime/three_ds_recomp/include/fast/oot3d').mkdir(parents=True)
                staging.apply(root)
                before = {name: (root / name).read_text() for name in files}
                staging.apply(root)
                self.assertEqual(before, {name: (root / name).read_text() for name in files})
                lifecycle = before[backend + 'gfx_vulkan_lifecycle.cpp']
                self.assertEqual(lifecycle.count('RetunedStartupStage(15);'), 1)
                self.assertNotIn('RetunedStartupStage(8);', lifecycle)
                self.assertEqual(lifecycle.count('CreateInstance();'), 1)
                self.assertEqual(before[native + 'oot3d_native_game.cpp'].count('RetunedStartupException(ex.what());'), 1)
