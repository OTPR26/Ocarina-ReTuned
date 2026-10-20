"""Buffer SDL playback and retain bounded native refresh debt."""
from pathlib import Path
import argparse
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reframed'))
from apply_native_port import edit

def apply(engine):
    assets=Path(__file__).with_name('audio')
    include=engine/'runtime/three_ds_recomp/include/ship/audio'
    (include/'pcm_buffer.h').write_text((assets/'pcm_buffer.h').read_text())
    (include/'retuned_output_gain.h').write_text((assets/'output_gain.h').read_text())
    header=include/'SDLAudioPlayer.h'
    edit(header,'#include "AudioPlayer.h"','#include "AudioPlayer.h"\n#include "pcm_buffer.h"')
    edit(header,'    int Buffered() override;', '    int Buffered() override;\n    uint64_t OutputUnderruns() const override;')
    edit(header,'    SDL_AudioDeviceID mDevice = 0;', '    Retuned::PcmBuffer mPcm;\n    SDL_AudioDeviceID mDevice = 0;')
    (engine/'runtime/three_ds_recomp/src/ship/audio/SDLAudioPlayer.cpp').write_text((assets/'SDLAudioPlayer.cpp').read_text())
    root=engine/'tools/oot3d/native_game_runtime'
    header=root/'oot3d_native_frame_rate.h'
    edit(header, '            NativeSimulationCatchUpPolicy::DropExcess);',
         '            NativeSimulationCatchUpPolicy::DropExcess,\n        uint32_t maximumRefreshes = kMaximumGuestRefreshesPerPresentation);')
    edit(header,'    NativePresentationSchedulerStats mStats;',
         '    uint32_t mMaximumRefreshes = kMaximumGuestRefreshesPerPresentation;\n    NativePresentationSchedulerStats mStats;')
    source=header.with_suffix('.cpp')
    edit(source,'    NativeSimulationCatchUpPolicy catchUpPolicy)\n    : mVisualSampleRateHz(visualSampleRateHz),',
         '    NativeSimulationCatchUpPolicy catchUpPolicy, uint32_t maximumRefreshes)\n    : mMaximumRefreshes(std::clamp(maximumRefreshes, 1U, kMaximumDeferredGuestRefreshes)),\n      mVisualSampleRateHz(visualSampleRateHz),')
    edit(source,'            kMaximumGuestRefreshesPerPresentation);','            mMaximumRefreshes);')
    setup=root/'oot3d_native_a32_window_setup.cpp'
    edit(setup,'''      frameRateContract.Mode ==
              Oot3dNativeGame::GameplayTimingMode::Enhanced60''',
         '''      (launch.UiProfile == Oot3dNativeGame::Oot3dUiProfile::Reframed ||
       frameRateContract.Mode == Oot3dNativeGame::GameplayTimingMode::Enhanced60)''')
    edit(setup,'''          : Oot3dNativeGame::NativeSimulationCatchUpPolicy::DropExcess);''',
         '''          : Oot3dNativeGame::NativeSimulationCatchUpPolicy::DropExcess,
      launch.UiProfile == Oot3dNativeGame::Oot3dUiProfile::Reframed
          ? 4U : Oot3dNativeGame::kMaximumGuestRefreshesPerPresentation);''')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('engine',type=Path)
    apply(p.parse_args().engine)
