"""Stage shared settings pages and their platform-specific controls."""
from pathlib import Path


def stage_platform_display_settings(engine):
    root = Path(engine) / 'runtime/three_ds_recomp'
    path = root / 'src/fast/oot3d/graphics_settings_window.cpp'
    source = path.read_text()
    # Migrate the former inline overlays; the shared page now owns their call.
    for condition in ('RetunedFrontend::AndroidDualProbeRequested()',
                      'RetunedFrontend::DuoProbeRequested() && RetunedFrontend::DuoDisplay.Available()'):
        marker = '        if(' + condition + ') {\n            ImGui::SeparatorText("Display");'
        if marker not in source:
            continue
        begin = source.index(marker)
        brace = source.index('{', begin)
        depth = 1
        end = brace + 1
        while depth and end < len(source):
            depth += (source[end] == '{') - (source[end] == '}')
            end += 1
        if depth:
            raise ValueError('Unterminated legacy display settings')
        source = source[:begin] + source[end:].lstrip('\n')
    include = '#include "fast/oot3d/retuned_platform_display_settings.h"\n'
    if include not in source:
        source = include + source
    call = '        RetunedFrontend::DrawPlatformDisplaySettings(config,RetunedFrontend::Toggle);\n'
    anchor = '        ImGui::SeparatorText("Menu");'
    if call not in source:
        if source.count(anchor) != 1:
            raise ValueError('General settings Menu anchor changed')
        source = source.replace(anchor, call + anchor)
    include_root = root / 'include/fast/oot3d'
    include_root.mkdir(parents=True, exist_ok=True)
    for source_name, target_name in (('platform_display_settings.h', 'retuned_platform_display_settings.h'),
                                     ('lower_equipment_state.h', 'lower_equipment_state.h')):
        destination = include_root / target_name
        contents = Path(__file__).with_name(source_name).read_bytes()
        if not destination.exists() or destination.read_bytes() != contents:
            destination.write_bytes(contents)
    if source != path.read_text():
        path.write_text(source)


def refresh_panel_draw(engine):
    path = Path(engine) / 'runtime/three_ds_recomp/src/fast/oot3d/graphics_settings_window.cpp'
    source = path.read_text()
    begin = source.index('void GraphicsSettingsPanel::Draw() {')
    end = source.index('\nvoid GraphicsSettingsPanel::DrawGrassSettings()', begin)
    canonical = Path(__file__).with_name('panel_draw.cpp.inc').read_text()
    updated = source[:begin] + canonical + source[end:]
    if updated != source:
        path.write_text(updated)
    stage_platform_display_settings(engine)


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
