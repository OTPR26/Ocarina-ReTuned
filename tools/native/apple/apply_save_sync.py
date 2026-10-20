"""Install the shared Apple save bridge into a prepared neutral engine."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'reframed'))
from apply_native_port import edit

def apply(engine):
    engine=Path(engine);source=Path(__file__).parent
    destination=engine/'ports/retuned-save-sync';destination.mkdir(parents=True,exist_ok=True)
    for name in ('save_sync.h','save_sync.mm','save_sync_policy.h','save_sync.cmake'):
        target=destination/name
        content=(source/name).read_text()
        if not target.exists() or target.read_text()!=content:target.write_text(content)
    launcher=source.parent/'macos_launcher.cpp'
    target=destination/'macos_launcher.cpp'
    if not target.exists() or target.read_text()!=launcher.read_text():target.write_text(launcher.read_text())
    entry=engine/'tools/oot3d/native_game_runtime/oot3d_native_game.cpp'
    text=entry.read_text();marker='#if defined(RETUNED_MAC_APP)\n#define main RetunedMacNativeMain\n#endif\n'
    if 'int main(int argc, char** argv)' in text and marker not in text:
        entry.write_text(text.replace('int main(int argc, char** argv)',marker+'int main(int argc, char** argv)',1))
    game=engine/'CMake/oot3d/game.cmake'
    marker='include("${CMAKE_CURRENT_SOURCE_DIR}/ports/retuned-save-sync/save_sync.cmake")'
    if marker not in game.read_text():game.write_text(game.read_text()+'\n'+marker+'\n')
    graphics=engine/'runtime/three_ds_recomp/src/fast/oot3d/graphics_settings_window.cpp'
    text=graphics.read_text();marker='#include "fast/oot3d/retuned_save_sync.h"'
    if marker not in text:graphics.write_text(marker+'\n'+text)
    runtime=engine/'tools/oot3d/native_game_runtime'
    include=engine/'runtime/three_ds_recomp/include/fast/oot3d/retuned_save_sync.h'
    content=(source/'save_sync.h').read_text()
    if not include.exists() or include.read_text()!=content:include.write_text(content)
    setup=runtime/'oot3d_native_a32_window_setup.cpp'
    edit(setup,'#include "retuned_reframed_settings.h"','#include "retuned_reframed_settings.h"\n#include "fast/oot3d/retuned_save_sync.h"')
    edit(setup,'  saveDataDirectory = hostConfig.SaveDataDirectory;',
         '  saveDataDirectory = hostConfig.SaveDataDirectory;\n  RetunedSaveSyncConfigure(saveDataDirectory.string().c_str());\n  hostConfig.SaveDataCommitted=[] {RetunedSaveSyncCommitted();};')
    host=runtime/'oot3d_native_a32_ctr_host.h'
    edit(host,'    std::filesystem::path SaveDataDirectory;',
         '    std::filesystem::path SaveDataDirectory;\n    std::function<void()> SaveDataCommitted;')
    fs=runtime/'oot3d_native_a32_ctr_host_fs.cpp'
    edit(fs,'                event.Name += ":ControlArchive:handle=0x";',
         '                if(result==kResultSuccess && action==0 && archive->Id==kFsSaveDataArchiveId && mConfig.SaveDataCommitted)mConfig.SaveDataCommitted();\n                event.Name += ":ControlArchive:handle=0x";')
    frame=runtime/'oot3d_native_a32_window_frame.cpp'
    edit(frame,'#include "retuned_reframed_settings.h"','#include "retuned_reframed_settings.h"\n#include "fast/oot3d/retuned_save_sync.h"')
    edit(frame,'bool NativeA32WindowSession::RunFrame() {','bool NativeA32WindowSession::RunFrame() {\n  RetunedSaveSyncTick(RetunedFrontend::StartupVisible);')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine',type=Path)
    apply(parser.parse_args().engine)
