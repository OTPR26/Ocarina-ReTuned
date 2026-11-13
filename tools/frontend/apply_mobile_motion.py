"""Feed Android and iOS device sensors through the shared native motion mapper."""
from pathlib import Path
from apply_native_port import edit


def apply(engine):
    engine = Path(engine)
    include = engine / 'runtime/three_ds_recomp/include/fast/oot3d'
    include.joinpath('retuned_mobile_device_motion.h').write_bytes(
        Path(__file__).with_name('mobile_device_motion.h').read_bytes())
    include.joinpath('retuned_android_controller_motion.h').write_bytes(
        Path(__file__).with_name('android_controller_motion.h').read_bytes())
    source = engine / 'tools/oot3d/native_game_runtime/oot3d_native_a32_window_input.cpp'
    edit(source, '#include "oot3d_native_a32_window_shared.h"',
         '#include "oot3d_native_a32_window_shared.h"\n#include "fast/oot3d/retuned_mobile_device_motion.h"')
    if 'RetunedFrontend::SampleMobileDeviceMotion(' not in source.read_text():
        edit(source, '  controls.ObserveMotion(host.ControllerMotion);',
             '  RetunedFrontend::SampleMobileDeviceMotion(host.ControllerMotion,\n'
             '      config.NativeAimSource == NativeMotionSource::Automatic ||\n'
             '      config.NativeAimSource == NativeMotionSource::ControllerMotion);\n'
             '  controls.ObserveMotion(host.ControllerMotion);')

    old = '      config.NativeAimSource == NativeMotionSource::ControllerMotion);'
    new = '      config.NativeAimSource == NativeMotionSource::ControllerMotion,\n      config.ControllerEnabled ? selectedController.Controller : nullptr);'
    if new not in source.read_text():
        edit(source, old, new)
    java = engine / 'ports/android/app/src/main/java/org/triaevum/android'
    if java.is_dir():
        for name in ('ControllerMotion.java','ControllerMotionState.java'):
            java.joinpath(name).write_bytes(Path(__file__).parents[1].joinpath('native/android',name).read_bytes())
        for name in ('RetunedGameActivity.java', 'TriAevumActivity.java'):
            activity = java / name
            if activity.exists() and 'private TouchOverlay touchOverlay;' in activity.read_text():
                if 'retunedControllerMotion(' not in activity.read_text():
                    edit(activity, '    private TouchOverlay touchOverlay;',
                         '    private TouchOverlay touchOverlay;\n'
                         '    public double[] retunedControllerMotion(String name,int vendor,int product){\n'
                         '        return touchOverlay==null?null:touchOverlay.controllerMotion.sample(name,vendor,product);\n'
                         '    }')

    composition=engine/'tools/three_ds/input/three_ds_motion_composition.cpp'
    if composition.exists():
        import runpy
        patch=Path(__file__).parents[1]/'native/apple/patch_motion_composition.py'
        runpy.run_path(str(patch))['apply'](engine)
