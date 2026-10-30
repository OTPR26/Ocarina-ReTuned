"""Feed Android and iOS device sensors through the shared native motion mapper."""
from pathlib import Path
from apply_native_port import edit


def apply(engine):
    engine = Path(engine)
    include = engine / 'runtime/three_ds_recomp/include/fast/oot3d'
    include.joinpath('retuned_mobile_device_motion.h').write_bytes(
        Path(__file__).with_name('mobile_device_motion.h').read_bytes())
    source = engine / 'tools/oot3d/native_game_runtime/oot3d_native_a32_window_input.cpp'
    edit(source, '#include "oot3d_native_a32_window_shared.h"',
         '#include "oot3d_native_a32_window_shared.h"\n#include "fast/oot3d/retuned_mobile_device_motion.h"')
    edit(source, '  controls.ObserveMotion(host.ControllerMotion);',
         '  RetunedFrontend::SampleMobileDeviceMotion(host.ControllerMotion,\n'
         '      config.NativeAimSource == NativeMotionSource::Automatic ||\n'
         '      config.NativeAimSource == NativeMotionSource::ControllerMotion);\n'
         '  controls.ObserveMotion(host.ControllerMotion);')
