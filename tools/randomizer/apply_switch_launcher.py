"""Install the startup launcher and statically linked Switch title selection."""
import argparse
from pathlib import Path
from apply_android_session import patch
from apply_host_services import BASE, apply
from apply_private_launcher import install_session_continue


def install(engine, source):
    root = Path(__file__).resolve().parent
    apply(engine)
    install_session_continue(engine)
    context = engine / 'runtime/three_ds_recomp/src/ship/Context.cpp'
    anchor = 'std::unique_ptr<Context> Context::mContext;'
    patch(context, anchor, anchor + '\nstatic std::shared_ptr<spdlog::logger> previousSessionLogger;')
    anchor = '        spdlog::register_logger(GetLogger());'
    patch(context, anchor, '        previousSessionLogger = spdlog::default_logger();\n' + anchor)
    anchor = '        mLogger->flush();'
    patch(context, anchor, anchor + """
        if (spdlog::get(mLogger->name()) == mLogger) {
            spdlog::drop(mLogger->name());
            spdlog::set_default_logger(std::move(previousSessionLogger));
        }""")
    runtime = engine / BASE
    gui = engine / 'runtime/three_ds_recomp/src/fast/Fast3dGui.cpp'
    patch(gui, '#include <SDL_vulkan.h>',
          '#include <SDL_vulkan.h>\n#include "switch_launcher.h"')
    anchor = '        RetunedFrontend::DrawStartup(*this,GetAnyGuiWindowVisible());'
    patch(gui, anchor, '        RetunedRandomizer::TickSwitchLauncher();\n' + anchor)
    window = runtime / 'oot3d_native_a32_window.cpp'
    anchor = '#include "oot3d_native_a32_window.h"'
    patch(window, anchor, anchor + '\n#include "switch_launcher.h"')
    patch(window, '    if (!RunFrame()) break;', '    if (RetunedRandomizer::SwitchHandoff.Pending() || !RunFrame()) break;')
    setup = runtime / 'oot3d_native_a32_window_setup.cpp'
    patch(setup, '#include <stb_image.h>', '#include <stb_image.h>\n#include "proof_profile.h"')
    patch(setup, 'RetunedFrontend::StartupVisible=launch.LoadStatePath.empty();',
          'RetunedFrontend::StartupVisible=launch.LoadStatePath.empty() && !std::getenv("RETUNED_RANDOMIZER_ACTIVE_SLOT") && !std::getenv("RETUNED_RANDOMIZER_START_NORMAL");')
    for anchor, call in (
        ('  saveDataDirectory = hostConfig.SaveDataDirectory;', 'BindProofProfileIfPresent(hostConfig, launch.A32ProcessManifestPath);'),
        ('  picaMemoryRegions = BuildPicaMemoryRegions(*manifest);', 'ActivateProofSeedIfPresent(process.Memory(), launch.A32ProcessManifestPath);'),
    ):
        patch(setup, anchor, '  RetunedRandomizer::' + call + '\n' + anchor)
    anchor = '  if (hdFontsLoaded) {'
    patch(setup, anchor, '  if (std::getenv("RETUNED_RANDOMIZER_ACTIVE_SLOT")) blockEntryHooks.push_back(kFileSelectUpdate);\n' + anchor)
    loader = runtime / 'oot3d_native_direct_aot.cpp'
    anchor = 'const Oot3dWholeAotProgramV2 *WholeAotProgram() noexcept {'
    patch(loader, anchor, '''extern "C" const Oot3dWholeAotProgramV2* retuned_switch_randomizer_query(uint32_t) noexcept __attribute__((weak));
const Oot3dWholeAotProgramV2 *SwitchWholeProgram(bool randomized) noexcept {''')
    anchor = '  static const Oot3dWholeAotProgramV2 *program = []() noexcept {'
    patch(loader, anchor, '  const Oot3dWholeAotProgramV2 *program = [randomized]() noexcept {')
    anchor = '        triaevum_title_whole_aot_query(kOot3dWholeAotPluginAbiV2);'
    patch(loader, anchor, '        randomized ? (retuned_switch_randomizer_query ? retuned_switch_randomizer_query(kOot3dWholeAotPluginAbiV2) : nullptr) :\n' + anchor)
    anchor = 'const Oot3dDirectAotProgramV1 *DirectAotProgram() noexcept {'
    patch(loader, anchor, '''const Oot3dWholeAotProgramV2 *WholeAotProgram() noexcept {
  if (std::getenv("RETUNED_RANDOMIZER_ACTIVE_SLOT")) {
    static const auto* randomized = SwitchWholeProgram(true);
    return randomized;
  }
  static const auto* normal = SwitchWholeProgram(false);
  return normal;
}

''' + anchor)
    patch(setup, '  InitContextForDemo(hostArgs);', """  const bool retainedContext = Ship::Context::GetRawInstance() != nullptr;
  if (!retainedContext) InitContextForDemo(hostArgs);""")
    anchor = '  auto &api = *apiPointer;'
    patch(setup, anchor, anchor + """
  if (retainedContext) {
    api.WaitForIdle();
    std::string error;
    if (!api.ResetPicaState(&error)) throw std::runtime_error("Cannot reset Switch graphics state: " + error);
  }""")
    anchor = '      dynamic_cast<Fast::Oot3d::TitleRenderBackend *>(&api);'
    patch(setup, anchor, anchor + """
  if (retainedContext && titleRenderBackend) {
    std::string error;
    if (!titleRenderBackend->ResetTitleState(&error)) throw std::runtime_error("Cannot reset Switch title state: " + error);
  }""")
    main = runtime / 'oot3d_native_game.cpp'
    patch(main, '        DestroyContextForDemo();\n#if defined(__SWITCH__)',
          '        if (!RetunedRandomizer::SwitchHandoff.Pending()) DestroyContextForDemo();\n#if defined(__SWITCH__)')
    patch(main, 'int main(int argc, char** argv) {', '#include "switch_launcher.h"\nstatic int RunSwitchGuest(int argc, char** argv) {')
    anchor = '            argv = homebrewArguments.data();'
    patch(main, anchor, anchor + '\n            RetunedRandomizer::SwitchNormalArgs.assign(argv+1, argv+argc);')
    if 'int RunSwitchSessions(' not in main.read_text():
        with main.open('a') as f:
            f.write((root / 'switch_sessions.cpp.inc').read_text())
    cmake = engine / 'CMakeLists.txt'
    if '# ReTuned Switch Randomizer' not in cmake.read_text():
        with cmake.open('a') as out:
            out.write(f'''
# ReTuned Switch Randomizer
set(RANDOMIZER_SOURCE "{source}" CACHE PATH "" FORCE)
set(RANDOMIZER_ENGINE "${{CMAKE_CURRENT_SOURCE_DIR}}" CACHE PATH "" FORCE)
add_subdirectory("{root}" randomizer)
foreach(target oot3d_native_game three_ds_recomp_runtime)
  target_include_directories(${{target}} PRIVATE "{root}" "${{CMAKE_CURRENT_SOURCE_DIR}}/runtime/triaevum_module/include" "${{CMAKE_CURRENT_SOURCE_DIR}}/runtime/three_ds_recomp/include/fast/oot3d")
  target_link_libraries(${{target}} PRIVATE retuned_randomizer_frontend)
endforeach()
''')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    parser.add_argument('--source', required=True, type=Path)
    args = parser.parse_args()
    install(args.engine.resolve(), args.source.resolve())
