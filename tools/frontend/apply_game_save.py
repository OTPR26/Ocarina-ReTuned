"""Stage native Save access without replacing platform-specific settings pages."""
from pathlib import Path
from apply_native_port import edit


def apply(engine):
    root = Path(engine)
    here = Path(__file__).parent
    include = root / 'runtime/three_ds_recomp/include/fast/oot3d'
    include.mkdir(parents=True, exist_ok=True)
    for name in ('game_save.h', 'game_save_menu.h', 'native_save_menu.h'):
        (include / ('retuned_' + name)).write_bytes((here / name).read_bytes())
    (include/'lower_equipment_state.h').write_bytes((here/'lower_equipment_state.h').read_bytes())
    runtime = root / 'tools/oot3d/native_game_runtime'
    frame = runtime / 'oot3d_native_a32_window_frame.cpp'
    marker = '#include "fast/oot3d/retuned_game_save.h"\n'
    if marker not in frame.read_text():
        frame.write_text(marker + frame.read_text())
    injection = (here / 'game_save_input.cpp.inc').read_text()
    contents=frame.read_text()
    anchor='  if (!inputTimeline.Enabled()) {'
    marker='  // Deliver the native Save input after the Settings shortcut is consumed.'
    if contents.count(anchor)!=1 or contents.count(marker)>1:
        raise ValueError('Save input routing context changed')
    begin=contents.index(marker) if marker in contents else contents.index(anchor)
    end=contents.index(anchor,begin)
    frame.write_text(contents[:begin]+injection+contents[end:])
    graphics = root / 'runtime/three_ds_recomp/src/fast/oot3d/graphics_settings_window.cpp'
    marker = '#include "fast/oot3d/retuned_game_save_menu.h"\n'
    if marker not in graphics.read_text():
        graphics.write_text(marker + graphics.read_text())
    marker = '#include "fast/oot3d/retuned_screen_probe.h"\n'
    if marker not in graphics.read_text():
        graphics.write_text(marker + graphics.read_text())
    gui = root / 'runtime/three_ds_recomp/src/fast/Fast3dGui.cpp'
    marker = '#include "fast/oot3d/retuned_game_save.h"\n'
    if marker not in gui.read_text():
        gui.write_text(marker + gui.read_text())
    edit(graphics, '      case SettingsPage::General: {\n',
         '      case SettingsPage::General: {\n'
         '        RetunedFrontend::DrawDualGameSave(RetunedFrontend::ProbeGuestDualActive.load(),!RetunedFrontend::StartupVisible);\n')

