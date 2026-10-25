"""Bind the private two-view renderer to an acknowledged ReFramed mode."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reframed'))
from apply_native_port import edit
from apply_screen_probe import apply as apply_renderer


def apply(engine):
    engine = Path(engine)
    apply_renderer(engine)
    runtime = engine / 'tools/oot3d/native_game_runtime'
    here = Path(__file__).parent
    for name in ('screen_presentation_bridge.h', 'reframed_screen_probe.h'):
        (runtime / ('retuned_' + name)).write_bytes((here / name).read_bytes())
    (runtime / 'retuned_screen_presentation_bridge.h').write_text('#pragma once\n#include "fast/oot3d/screen_presentation_bridge.h"\n')
    marker = '#include "retuned_reframed_screen_probe.h"\n'
    for name in ('setup', 'frame'):
        path = runtime / ('oot3d_native_a32_window_' + name + '.cpp')
        text = path.read_text()
        if marker not in text:
            path.write_text(marker + text)
    edit(runtime / 'oot3d_native_a32_window_setup.cpp',
         'RetunedFrontend::Current().Initialize(launch.A32ProcessManifestPath);',
         'RetunedFrontend::Current().Initialize(launch.A32ProcessManifestPath);\n'
         '  if (launch.UiProfile == Oot3dNativeGame::Oot3dUiProfile::Reframed)\n'
         '    RetunedFrontend::NativeScreenProbe.Initialize(launch.A32ProcessManifestPath);')
    edit(runtime / 'oot3d_native_a32_window_frame.cpp',
         '  if(RetunedFrontend::NativeFrontendEnabled && RetunedFrontend::StartupVisible) {',
         '  if (RetunedFrontend::ProbeGuestBridgeBound.load()) RetunedFrontend::StartupVisible = false;\n'
         '  if(RetunedFrontend::NativeFrontendEnabled && RetunedFrontend::StartupVisible) {')
    edit(runtime / 'oot3d_native_a32_window_frame.cpp',
         '  const auto hidUpdate = hostServices.AdvanceHidToCurrentTick(',
         '  if (RetunedFrontend::NativeScreenProbe.Apply(process, frameCount)) {\n'
         '    inputFrame.Hid.TouchPressed = false;\n'
         '    inputFrame.Hid.TouchX = inputFrame.Hid.TouchY = 0;\n'
         '    UpdateScenePresentation();\n'
         '  }\n'
         '  const auto hidUpdate = hostServices.AdvanceHidToCurrentTick(')


if __name__ == '__main__':
    apply(Path(sys.argv[1]))
