#!/usr/bin/env python3
"""Wire the opt-in launcher into the existing private Mac proof engine."""
from pathlib import Path
import argparse
from apply_host_services import replace, BASE

def install_session_continue(engine):
    shared=engine/BASE/'oot3d_native_a32_window_shared.h'
    text=shared.read_text()
    text=replace(text,'#pragma once','#pragma once\n#include "continue_game.h"\n#include <cstdlib>')
    anchor='struct NativeWidescreenProjectionState {\n'
    text=replace(text,anchor,anchor+"""  RetunedRandomizer::ContinueGame RandomizerContinue{
      std::getenv("RETUNED_RANDOMIZER_ACTIVE_SLOT") != nullptr,
      std::getenv("RETUNED_RANDOMIZER_NEW_GAME") != nullptr};
""")
    policy=engine/BASE/'oot3d_native_a32_projection_policy.cpp'
    policyText=policy.read_text()
    old="""  static RetunedRandomizer::ContinueGame randomizerContinue(
      std::getenv("RETUNED_RANDOMIZER_ACTIVE_SLOT") != nullptr,
      std::getenv("RETUNED_RANDOMIZER_NEW_GAME") != nullptr);
  if(randomizerContinue.Update(pc,memory))
    std::fprintf(stderr,"Randomizer Continue: native file zero load queued\\n");
"""
    policyText=policyText.replace(old,'')
    anchor='  auto &runtime = *static_cast<NativeWidescreenProjectionState *>(user);'
    policyText=replace(policyText,anchor,anchor+"""
  if(runtime.RandomizerContinue.Update(pc,memory))
    std::fprintf(stderr,"Randomizer Continue: native file zero load queued\\n");
""")
    shared.write_text(text)
    policy.write_text(policyText)

def install(engine):
    source=Path(__file__).resolve().parent
    gui=engine/'runtime/three_ds_recomp/src/fast/Fast3dGui.cpp'
    text=gui.read_text()
    text=replace(text,'#include <SDL_vulkan.h>','#include <SDL_vulkan.h>\n#include "private_launcher.h"')
    anchor='        RetunedFrontend::DrawStartup(*this,GetAnyGuiWindowVisible());'
    text=replace(text,anchor,'        RetunedRandomizer::TickPrivateLauncher();\n'+anchor)
    gui.write_text(text)
    setup=engine/BASE/'oot3d_native_a32_window_setup.cpp'
    text=setup.read_text().replace('  RetunedRandomizer::BindProofProfile(hostConfig, launch.A32ProcessManifestPath);',
        '  RetunedRandomizer::BindProofProfileIfPresent(hostConfig, launch.A32ProcessManifestPath);')
    mount='  picaMemoryRegions = BuildPicaMemoryRegions(*manifest);'
    text=replace(text,mount,'  RetunedRandomizer::ActivateProofSeedIfPresent(process.Memory(), launch.A32ProcessManifestPath);\n'+mount)
    setup.write_text(text)
    install_session_continue(engine)
    setup=engine/BASE/'oot3d_native_a32_window_setup.cpp'
    text=setup.read_text()
    anchor='  if (hdFontsLoaded) {'
    text=replace(text,anchor,'  if(std::getenv("RETUNED_RANDOMIZER_ACTIVE_SLOT")) blockEntryHooks.push_back(kFileSelectUpdate);\n'+anchor)
    setup.write_text(text)
    cmake=engine/'CMakeLists.txt';text=cmake.read_text()
    marker='# Private randomizer launcher integration.'
    if marker not in text:
        text+='\n'+marker+f'''
target_include_directories(three_ds_recomp_runtime PRIVATE "{source}" "${{CMAKE_SOURCE_DIR}}/runtime/triaevum_module/include" "${{CMAKE_SOURCE_DIR}}/runtime/three_ds_recomp/include/fast/oot3d")
target_sources(three_ds_recomp_runtime PRIVATE "{source}/run_catalog.cpp" "{source}/run_launcher.cpp")
'''
        cmake.write_text(text)
    cmake=engine/'CMakeLists.txt';text=cmake.read_text()
    seed_source=f'target_sources(oot3d_native_game PRIVATE "{source}/seed_activation.cpp")'
    if seed_source not in text:cmake.write_text(text+'\n'+seed_source+'\n')
    transfer_source=f'target_sources(three_ds_recomp_runtime PRIVATE "{source}/run_transfer.cpp")'
    text=cmake.read_text()
    if transfer_source not in text:cmake.write_text(text+'\n'+transfer_source+'\n')
    native_sources=f'target_sources(three_ds_recomp_runtime PRIVATE "{source}/seed_activation.cpp")' 
    text=cmake.read_text()
    if native_sources not in text:
        text+='\n'+native_sources+'\n'
        library=source.parents[1]/'work/private/randomizer/build/libretuned_randomizer.a'
        text+=f'target_link_libraries(three_ds_recomp_runtime PRIVATE "{library}")\n'
        cmake.write_text(text)
    dest=engine/'runtime/three_ds_recomp/include/fast/oot3d'  
    for name in ('randomizer_model.h','randomizer_ui.h','frontend_state.h','startup_draw.h','settings_pages.h'):
        (dest/('retuned_'+name)).write_bytes((source.parent/'frontend'/name).read_bytes())

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('engine',type=Path)
    install(parser.parse_args().engine.resolve())
