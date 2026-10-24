"""Use a radial dead zone so turning the stick does not add axial slowdown."""
from pathlib import Path
from apply_native_port import edit

def apply(engine):
    folder = Path(engine) / 'tools/three_ds/input'
    (folder / 'retuned_movement_stick.h').write_text(
        Path(__file__).with_name('movement_stick.h').read_text())
    source = folder / 'three_ds_input.cpp'
    edit(source, '#include "three_ds_input.h"',
         '#include "three_ds_input.h"\n#include "retuned_movement_stick.h"')
    before = '''    const std::int16_t analogX = ConvertHostAxisToNative(
        SelectConfiguredStickAxis(config.CirclePadSource,
                                  physical.LeftStickX,
                                  physical.RightStickX),
        config.CirclePadDeadZonePercent);
    const std::int16_t analogY = ConvertHostAxisToNative(
        SelectConfiguredStickAxis(config.CirclePadSource,
                                  physical.LeftStickY,
                                  physical.RightStickY),
        config.CirclePadDeadZonePercent);'''
    after = '''    const auto movement = RetunedFrontend::MapMovementStick(
        SelectConfiguredStickAxis(config.CirclePadSource, physical.LeftStickX, physical.RightStickX),
        SelectConfiguredStickAxis(config.CirclePadSource, physical.LeftStickY, physical.RightStickY),
        config.CirclePadDeadZonePercent, kNativeStickMaximum);
    const auto analogX = movement[0];
    const auto analogY = movement[1];'''
    edit(source, before, after)
