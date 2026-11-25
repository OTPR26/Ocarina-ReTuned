#!/usr/bin/env python3
"""Wire the Android randomizer host into an explicitly selected test engine."""
import argparse
from pathlib import Path
from apply_host_services import apply, replace, BASE
from apply_private_launcher import install_session_continue


def install(engine, source, *, private_test=False):
    apply(engine)
    here=Path(__file__).resolve().parent
    headers=engine/"runtime/three_ds_recomp/include/fast/oot3d"
    (headers/"retuned_android_save_files.h").write_bytes((here.parent/"native/android/save_files_ui.h").read_bytes())
    gui=engine/'runtime/three_ds_recomp/src/fast/Fast3dGui.cpp'
    text=gui.read_text().replace('#include "private_launcher.h"', '#include "android_launcher.h"')
    text=text.replace('RetunedRandomizer::TickPrivateLauncher();','RetunedRandomizer::TickAndroidLauncher();')
    if '#include "android_launcher.h"' not in text:
        text=replace(text,'#include <SDL_vulkan.h>','#include <SDL_vulkan.h>\n#include "android_launcher.h"')
        anchor='        RetunedFrontend::DrawStartup(*this,GetAnyGuiWindowVisible());'
        text=replace(text,anchor,'        RetunedRandomizer::TickAndroidLauncher();\n'+anchor)
    gui.write_text(text)
    setup=engine/BASE/'oot3d_native_a32_window_setup.cpp'
    text=setup.read_text()
    text=replace(text,'#include <stb_image.h>','#include <stb_image.h>\n#include "proof_profile.h"')
    marker='  saveDataDirectory = hostConfig.SaveDataDirectory;'
    if 'BindProofProfileIfPresent' not in text:
        text=replace(text,marker,'  RetunedRandomizer::BindProofProfileIfPresent(hostConfig, launch.A32ProcessManifestPath);\n'+marker)
    mount='  picaMemoryRegions = BuildPicaMemoryRegions(*manifest);'
    text=replace(text,mount,'  RetunedRandomizer::ActivateProofSeedIfPresent(process.Memory(), launch.A32ProcessManifestPath);\n'+mount)
    text=replace(text,'  if (hdFontsLoaded) {','  if(std::getenv("RETUNED_RANDOMIZER_ACTIVE_SLOT")) blockEntryHooks.push_back(kFileSelectUpdate);\n  if (hdFontsLoaded) {')
    setup.write_text(text)
    install_session_continue(engine)
    from apply_android_session import install as install_session
    install_session(engine)
    from apply_legacy_hud_anchor import install as install_anchor
    install_anchor(engine)
    from apply_shoulder_glass import install as install_shoulder
    install_shoulder(engine)
    cmake=engine/'CMakeLists.txt'
    text=cmake.read_text()
    marker='# Android randomizer test integration.'
    test_definition='  target_compile_definitions(${target} PRIVATE RETUNED_RANDOMIZER_PRIVATE_TEST=1)\n'
    if marker in text:
        start=text.index(marker)
        section=text[start:].replace(test_definition,'',1)
        if private_test:
            section=section.replace('endforeach()',test_definition+'endforeach()',1)
        cmake.write_text(text[:start]+section)
    else:
        definition=test_definition if private_test else ''
        text+='\n'+marker+f'''
set(RANDOMIZER_SOURCE "{source}" CACHE PATH "" FORCE)
set(RANDOMIZER_ENGINE "{engine}" CACHE PATH "" FORCE)
add_subdirectory("{here}" randomizer)
foreach(target oot3d_native_game three_ds_recomp_runtime)
  target_include_directories(${{target}} PRIVATE "{here}" "${{CMAKE_CURRENT_SOURCE_DIR}}/runtime/triaevum_module/include" "${{CMAKE_CURRENT_SOURCE_DIR}}/runtime/three_ds_recomp/include/fast/oot3d")
  target_link_libraries(${{target}} PRIVATE retuned_randomizer_frontend)
{definition}endforeach()
'''
        cmake.write_text(text)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('engine',type=Path)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--private-test',action='store_true')
    args=parser.parse_args()
    install(args.engine.resolve(),args.source.resolve(),private_test=args.private_test)
