#!/usr/bin/env python3
"""Wire the in-app Randomizer launcher and Apple guest handoff."""
import argparse
from pathlib import Path
from apply_android_session import install_session_loader, patch
from apply_host_services import BASE, apply
from apply_private_launcher import install_session_continue


def install(engine, source):
    root = Path(__file__).resolve().parent
    runtime = engine / BASE
    apply(engine)
    install_session_continue(engine)
    gui = engine / 'runtime/three_ds_recomp/src/fast/Fast3dGui.cpp'
    patch(gui, '#include <SDL_vulkan.h>', '#include <SDL_vulkan.h>\n#include "apple_launcher.h"')
    anchor = '        RetunedFrontend::DrawStartup(*this,GetAnyGuiWindowVisible());'
    patch(gui, anchor, '        RetunedRandomizer::TickAppleLauncher();\n' + anchor)
    window = runtime / 'oot3d_native_a32_window.cpp'
    patch(window, '#include "oot3d_native_a32_window.h"',
          '#include "oot3d_native_a32_window.h"\n#include "apple_launcher.h"')
    patch(window, '    if (!RunFrame()) break;',
          '    if (RetunedRandomizer::AppleSessions.Pending() || !RunFrame()) break;')
    setup = runtime / 'oot3d_native_a32_window_setup.cpp'
    patch(setup, '#include <stb_image.h>', '#include <stb_image.h>\n#include "proof_profile.h"')
    anchor = '  saveDataDirectory = hostConfig.SaveDataDirectory;'
    patch(setup, anchor, '  RetunedRandomizer::BindProofProfileIfPresent(hostConfig, launch.A32ProcessManifestPath);\n' + anchor)
    anchor = '  picaMemoryRegions = BuildPicaMemoryRegions(*manifest);'
    patch(setup, anchor, '  RetunedRandomizer::ActivateProofSeedIfPresent(process.Memory(), launch.A32ProcessManifestPath);\n' + anchor)
    patch(setup, '  if (hdFontsLoaded) {',
          '  if (std::getenv("RETUNED_RANDOMIZER_ACTIVE_SLOT")) blockEntryHooks.push_back(kFileSelectUpdate);\n  if (hdFontsLoaded) {')
    patch(setup, '    RetunedFrontend::StartupVisible=launch.LoadStatePath.empty();',
          '    RetunedFrontend::StartupVisible=launch.LoadStatePath.empty() && !std::getenv("RETUNED_RANDOMIZER_ACTIVE_SLOT");')
    patch(setup, '  InitContextForDemo(hostArgs);', '''  const bool retainedContext = Ship::Context::GetRawInstance() != nullptr;
  if (!retainedContext) InitContextForDemo(hostArgs);''')
    patch(setup, '  auto &api = *apiPointer;', '''  auto &api = *apiPointer;
  if (retainedContext) {
    api.WaitForIdle();
    std::string error;
    if (!api.ResetPicaState(&error)) throw std::runtime_error("Could not reset renderer: " + error);
  }''')
    anchor = '      dynamic_cast<Fast::Oot3d::TitleRenderBackend *>(&api);'
    patch(setup, anchor, anchor + '''
  if (retainedContext && titleRenderBackend) {
    std::string error;
    if (!titleRenderBackend->ResetTitleState(&error)) throw std::runtime_error("Could not reset title: " + error);
  }''')
    main = runtime / 'oot3d_native_game.cpp'
    patch(main, '#include "oot3d_demo_host_context.h"', '#include "oot3d_demo_host_context.h"\n#include "apple_launcher.h"')
    patch(main, '        DestroyContextForDemo();\n#if defined(__SWITCH__)',
          '        if (!RetunedRandomizer::AppleSessions.Pending()) DestroyContextForDemo();\n#if defined(__SWITCH__)')
    install_session_loader(runtime)
    apple = engine / 'ports/apple/apple_main.mm'
    patch(apple, '#include "background_failure.h"', '#include "background_failure.h"\n#include "apple_launcher.h"')
    patch(apple, '#include "apple_launcher.h"', '#include "apple_launcher.h"\n#include "triaevum_title_plugin_loader.h"')
    previous_seed_copy = '''        std::filesystem::create_directories(std::filesystem::path(data.UTF8String) / "randomizer");
        NSData* seed = [NSData dataWithContentsOfFile:[privateRoot stringByAppendingPathComponent:@"seed.json"]];
        if (!seed || ![seed writeToFile:[data stringByAppendingPathComponent:@"seed.json"] options:NSDataWritingAtomic error:&error])
            return RetunedPresentAppleStartupIssue(RetunedAppleStartupInvalidSetup);
'''
    source_text = apple.read_text()
    if previous_seed_copy in source_text:
        apple.write_text(source_text.replace(previous_seed_copy, '', 1))
    patch(apple, '        std::string profile=', '''        NSString* alternate = [privateRoot stringByAppendingPathComponent:@"Randomizer"];
        BOOL combined = [files fileExistsAtPath:alternate];
        const bool testHost = [NSBundle.mainBundle.bundleIdentifier isEqualToString:@"io.github.otpr26.ocarinaretuned.randomizer-test"];
        SDL_setenv("RETUNED_APPLE_TEST_HOST", testHost ? "1" : "0", 1);
        NSString* seedRoot = combined ? alternate : privateRoot;
        if (combined || [files fileExistsAtPath:[seedRoot stringByAppendingPathComponent:@"seed.json"]]) {
            NSString* destination = combined ? [data stringByAppendingPathComponent:@"randomizer/installed"] : data;
            if (![files createDirectoryAtPath:destination withIntermediateDirectories:YES attributes:nil error:&error])
                return RetunedPresentAppleStartupIssue(RetunedAppleStartupStorageError);
            if (combined) {
                NSData* bytes = [NSData dataWithContentsOfFile:[alternate stringByAppendingPathComponent:@"process-manifest.json"]];
                id doc = bytes ? [NSJSONSerialization JSONObjectWithData:bytes options:0 error:&error] : nil;
                if (![doc isKindOfClass:NSDictionary.class]) return RetunedPresentAppleStartupIssue(RetunedAppleStartupInvalidSetup);
                NSData* resolved = [NSJSONSerialization dataWithJSONObject:ResolvePaths(doc,bundle,data) options:0 error:&error];
                if (!resolved || ![resolved writeToFile:[destination stringByAppendingPathComponent:@"process-manifest.json"] options:NSDataWritingAtomic error:&error])
                    return RetunedPresentAppleStartupIssue(RetunedAppleStartupStorageError);
            }
            NSData* seed = [NSData dataWithContentsOfFile:[seedRoot stringByAppendingPathComponent:@"seed.json"]];
            if (!seed || ![seed writeToFile:[destination stringByAppendingPathComponent:@"seed.json"] options:NSDataWritingAtomic error:&error])
                return RetunedPresentAppleStartupIssue(RetunedAppleStartupInvalidSetup);
        }
        std::string profile=''')
    if '            auto next = RetunedRandomizer::AppleSessions.Take();' not in apple.read_text():
        patch(apple, '        const int result=RetunedNativeMain(static_cast<int>(pointers.size()),pointers.data());', '''        int result;
        for (;;) {
            pointers.clear();
            for (auto& argument : arguments) pointers.push_back(argument.data());
            result = RetunedNativeMain(static_cast<int>(pointers.size()), pointers.data());
            auto next = RetunedRandomizer::AppleSessions.Take();
            if (result || !next) break;
            RetunedRandomizer::AppleHost.reset();
            RetunedFrontend::RandomizerMenu = {};
            SDL_setenv("RETUNED_RANDOMIZER_ACTIVE_SLOT", std::to_string(next->randomizerSlot).c_str(), 1);
            SDL_setenv(next->newGame ? "RETUNED_RANDOMIZER_NEW_GAME" : "RETUNED_RANDOMIZER_CONTINUE", "1", 1);
            RetunedFrontend::StartupVisible = false;
            RetunedFrontend::SetupVisible = false;
            arguments = std::move(next->arguments);
            arguments.insert(arguments.begin(), "OcarinaReTuned");
        }''')
    patch(apple, '            RetunedRandomizer::AppleHost.reset();',
          '            RetunedRandomizer::AppleHost.reset();\n            Oot3dNativeGame::ResetTitlePluginForSession();')
    headers = engine / 'runtime/three_ds_recomp/include/fast/oot3d'
    for name in ('randomizer_model.h', 'randomizer_ui.h', 'frontend_state.h', 'startup_draw.h', 'settings_pages.h'):
        (headers / ('retuned_' + name)).write_bytes((root.parent / 'frontend' / name).read_bytes())
    from apply_legacy_hud_anchor import install as install_hud_anchor
    from apply_shoulder_glass import install as install_hud_glass
    install_hud_anchor(engine)
    install_hud_glass(engine)
    cmake = engine / 'CMakeLists.txt'
    marker = '# Private Apple Randomizer launcher.'
    if marker not in cmake.read_text():
        with cmake.open('a') as output:
            output.write(f'''
{marker}
set(RANDOMIZER_SOURCE "{source}" CACHE PATH "" FORCE)
set(RANDOMIZER_ENGINE "${{CMAKE_CURRENT_SOURCE_DIR}}" CACHE PATH "" FORCE)
add_subdirectory("{root}" randomizer)
foreach(target oot3d_native_game three_ds_recomp_runtime)
  target_include_directories(${{target}} PRIVATE "{root}" "${{CMAKE_CURRENT_SOURCE_DIR}}/runtime/triaevum_module/include" "${{CMAKE_CURRENT_SOURCE_DIR}}/runtime/three_ds_recomp/include/fast/oot3d")
  target_link_libraries(${{target}} PRIVATE retuned_randomizer_frontend)
endforeach()
''')

    marker = '# Advertise support for bundled Randomizer sessions.'
    if marker not in cmake.read_text():
        with cmake.open('a') as output:
            output.write('\n' + marker + '''
add_custom_command(TARGET oot3d_native_game POST_BUILD
  COMMAND "${CMAKE_COMMAND}" -E touch "$<TARGET_BUNDLE_DIR:oot3d_native_game>/randomizer-launcher-v1"
  VERBATIM)
''')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    install(args.engine.resolve(), args.source.resolve())
