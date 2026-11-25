"""Install the Mac launcher for locally prepared normal and Randomizer games."""
import argparse
from pathlib import Path
from apply_android_session import patch
from apply_host_services import BASE, apply
from apply_private_launcher import install_session_continue


def install(engine, source):
    root = Path(__file__).resolve().parent
    apply(engine)
    install_session_continue(engine)
    bootstrap = engine / 'ports/retuned-setup/first_run.cpp'
    anchor = '    preparationProfile=std::filesystem::absolute(profile);'
    patch(bootstrap, anchor, anchor + '\n    SDL_setenv("RETUNED_NORMAL_LAUNCH_PROFILE",Text(preparationProfile).c_str(),1);')
    gui = engine / 'runtime/three_ds_recomp/src/fast/Fast3dGui.cpp'
    patch(gui, '#include <SDL_vulkan.h>', '#include <SDL_vulkan.h>\n#include "mac_launcher.h"')
    anchor = '        RetunedFrontend::DrawStartup(*this,GetAnyGuiWindowVisible());'
    patch(gui, anchor, '        RetunedRandomizer::TickMacLauncher();\n' + anchor)
    setup = engine / BASE / 'oot3d_native_a32_window_setup.cpp'
    patch(setup, '#include <stb_image.h>', '#include <stb_image.h>\n#include "proof_profile.h"')
    for anchor, call in (
        ('  saveDataDirectory = hostConfig.SaveDataDirectory;', 'BindProofProfileIfPresent(hostConfig, launch.A32ProcessManifestPath);'),
        ('  picaMemoryRegions = BuildPicaMemoryRegions(*manifest);', 'ActivateProofSeedIfPresent(process.Memory(), launch.A32ProcessManifestPath);'),
    ):
        patch(setup, anchor, '  RetunedRandomizer::' + call + '\n' + anchor)
    anchor = '  if (hdFontsLoaded) {'
    patch(setup, anchor, '  if (std::getenv("RETUNED_RANDOMIZER_ACTIVE_SLOT")) blockEntryHooks.push_back(kFileSelectUpdate);\n' + anchor)
    from apply_legacy_hud_anchor import install as install_anchor
    from apply_shoulder_glass import install as install_glass
    install_anchor(engine)
    install_glass(engine)
    cmake = engine / 'CMakeLists.txt'
    marker = '# ReTuned Mac Randomizer'
    if marker not in cmake.read_text():
        with cmake.open('a') as out:
            out.write(f'''
{marker}
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
