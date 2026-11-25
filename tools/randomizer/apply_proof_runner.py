#!/usr/bin/env python3
"""Opt a private desktop engine into the isolated randomizer proof runner."""
import argparse
from pathlib import Path
from apply_host_services import apply, replace, BASE

def install(engine):
    apply(engine)
    source=Path(__file__).resolve().parent
    path=engine/BASE/'oot3d_native_a32_window_setup.cpp'
    text=path.read_text()
    text=replace(text,'#include <stb_image.h>','#include <stb_image.h>\n#include "proof_profile.h"')
    marker='  saveDataDirectory = hostConfig.SaveDataDirectory;'
    text=replace(text,marker,'''  if (!launch.LoadStatePath.empty() || !launch.ConvertStatePath.empty())
    throw std::runtime_error("Randomizer proof does not support save states");
  RetunedRandomizer::BindProofProfile(hostConfig, launch.A32ProcessManifestPath);
'''+marker)
    path.write_text(text)
    states=engine/BASE/'oot3d_native_a32_window_savestate.cpp'
    text=states.read_text()
    save='                                  const std::string *storedSettings) {\n'
    text=replace(text,save,save+'  return FailSave("Save states are disabled in the randomizer proof");\n')
    load='                                       bool applySettings) {\n'
    text=replace(text,load,load+'  lastSavestateMessage="Save states are disabled in the randomizer proof"; return false;\n')
    states.write_text(text)
    cmake=engine/'CMakeLists.txt';text=cmake.read_text()
    marker='# Isolated randomizer proof runner (private engine only).'
    if marker not in text:
        text+='\n'+marker+f'''
target_include_directories(oot3d_native_game PRIVATE "{source}" "${{CMAKE_SOURCE_DIR}}/runtime/triaevum_module/include")
target_sources(oot3d_native_game PRIVATE "{source}/save_store.cpp" "{source}/runtime_services.cpp" "${{CMAKE_SOURCE_DIR}}/runtime/triaevum_module/src/sha256.cpp")
set_target_properties(oot3d_native_game PROPERTIES OUTPUT_NAME "ReTunedRandomizerTest")
'''
        cmake.write_text(text)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('engine',type=Path);install(p.parse_args().engine.resolve())
