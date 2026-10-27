"""Refresh shared Mods contents without replacing platform-specific settings."""
from pathlib import Path


def refresh_mods_page(engine):
    path = Path(engine) / 'runtime/three_ds_recomp/src/fast/oot3d/graphics_settings_window.cpp'
    source = path.read_text()
    canonical = Path(__file__).with_name('panel_draw.cpp.inc').read_text()
    start, end = '      case SettingsPage::Mods:', '      case SettingsPage::About:'
    if source.count(end) != 1 or source.count(start) > 1:
        raise ValueError('Shared settings-page anchors changed')
    replacement = canonical[canonical.index(start):canonical.index(end)]
    begin = source.index(start) if start in source else source.index(end)
    updated = source[:begin] + replacement + source[source.index(end):]
    if updated != source:
        path.write_text(updated)
