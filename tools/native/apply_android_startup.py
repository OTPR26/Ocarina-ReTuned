"""Add bounded startup milestones without changing rendering or memory policy."""
from pathlib import Path
import shutil


def apply(engine):
    engine = Path(engine)
    include = '#include "fast/oot3d/retuned_startup_diagnostics.h"\n'
    destination = engine / 'runtime/three_ds_recomp/include/fast/oot3d/retuned_startup_diagnostics.h'
    shutil.copy2(Path(__file__).parent / 'android/startup_diagnostics.h', destination)

    def mark(relative, before, after):
        path = engine / relative
        text = path.read_text()
        if after not in text:
            if text.count(before) != 1:
                raise ValueError('Startup checkpoint context changed: ' + relative)
            text = text.replace(before, after)
        if include not in text:
            text = include + text
        path.write_text(text)

    native = 'tools/oot3d/native_game_runtime/'
    setup = native + 'oot3d_native_a32_window_setup.cpp'
    mark(native + 'oot3d_native_game.cpp', '        InitializeAndroidGameHost();',
         '        RetunedStartupStage(0);\n        InitializeAndroidGameHost();')
    mark(native + 'oot3d_native_game.cpp',
         '        if (!Oot3dNativeGame::Oot3dWholeAotPluginV2Available()) {',
         '        RetunedStartupStage(1);\n        if (!Oot3dNativeGame::Oot3dWholeAotPluginV2Available()) {')
    mark(native + 'oot3d_native_game.cpp', '    } catch (const std::exception& ex) {',
         '    } catch (const std::exception& ex) {\n        RetunedStartupStage(14);')
    mark(setup, 'void NativeA32WindowSession::Setup() {',
         'void NativeA32WindowSession::Setup() {\n  RetunedStartupStage(2);')
    mark(setup, '  manifest = Oot3dNativeGame::LoadNativeA32ProcessImageManifest(',
         '  RetunedStartupStage(3);\n  manifest = Oot3dNativeGame::LoadNativeA32ProcessImageManifest(')
    mark(setup, '  {\n    const auto fontPath =', '  RetunedStartupStage(4);\n  {\n    const auto fontPath =')
    mark(setup, '  auto &process = processStorage.emplace(',
         '  RetunedStartupStage(5);\n  auto &process = processStorage.emplace(')
    mount = ('  if (!Oot3dNativeGame::MountNativeA32ProcessImage(\n'
             '          process, *manifest, std::filesystem::path{}, &error)) {\n'
             '    throw std::runtime_error(error);\n  }')
    mark(setup, mount, mount + '\n  RetunedStartupStage(6);')
    mark(setup, '  InitContextForDemo(hostArgs);',
         '  RetunedStartupStage(7);\n  InitContextForDemo(hostArgs);')
    mark(setup, '  programPreparation =\n', '  RetunedStartupStage(10);\n  programPreparation =\n')
    mark(setup, '    processResult =\n        RunUntilGuestWait(process, launch.WholeAotBlockBudget);',
         '    RetunedStartupStage(11);\n    processResult =\n        RunUntilGuestWait(process, launch.WholeAotBlockBudget);\n    RetunedStartupStage(12);')
    vulkan = 'runtime/three_ds_recomp/src/fast/backends/gfx_vulkan_lifecycle.cpp'
    mark(vulkan, '    CreateInstance();', '    RetunedStartupStage(8);\n    CreateInstance();')
    mark(vulkan, '    CreateSwapchainResources();',
         '    RetunedStartupStage(9);\n    CreateSwapchainResources();')
    mark('runtime/three_ds_recomp/src/fast/backends/gfx_vulkan_device.cpp',
         '    // Release logs keep warnings only; the device is what a tester\'s report',
         '    RetunedStartupGraphics(properties.apiVersion, properties.vendorID, properties.driverVersion);\n'
         '    // Release logs keep warnings only; the device is what a tester\'s report')
    mark(native + 'oot3d_native_a32_window_frame.cpp', 'bool NativeA32WindowSession::RunFrame() {',
         'bool NativeA32WindowSession::RunFrame() {\n#ifdef __ANDROID__\n  static bool startupFrameReported = false;\n  if (!startupFrameReported) { startupFrameReported = true; RetunedStartupStage(13); }\n#endif')
