"""Expose pixel-based gameplay resolutions, including 720p on a 4K display."""
from pathlib import Path
from apply_native_port import edit


def apply(engine):
    root = Path(engine) / 'runtime/three_ds_recomp'
    include = root / 'include/fast/oot3d'
    graphics = root / 'src/fast/oot3d'
    source = Path(__file__).parent
    (include / 'retuned_render_resolution.h').write_text((source / 'render_resolution.h').read_text())

    def add_header(path):
        marker = '#include "fast/oot3d/retuned_render_resolution.h"'
        text = path.read_text()
        if marker not in text:
            path.write_text(marker + '\n' + text)

    policy = include / 'render_resolution_policy.h'
    add_header(policy)
    edit(policy, 'std::clamp(settings.InternalResolutionScale, 0.5F, 2.0F)',
         'RetunedFrontend::GameplayScale(settings.InternalResolutionScale)')
    edit(policy, "// of the output per axis. The user's own render scale stays within 0.5-2.",
         "// of the output per axis. Manual scaling also permits 720p on a 4K display.")
    validation = graphics / 'graphics_settings.cpp'
    add_header(validation)
    edit(validation, 'std::clamp(value.InternalResolutionScale, 0.5F, 2.0F)',
         'RetunedFrontend::GameplayScale(value.InternalResolutionScale)')
    runtime = graphics / 'graphics_settings_runtime.cpp'
    add_header(runtime)
    edit(runtime, 'parsed >= 0.5F', 'parsed >= RetunedFrontend::MinimumRenderScale')
    edit(runtime, 'initial.InternalResolutionScale = defaults.InternalResolutionScale;',
         'initial.InternalResolutionScale = RetunedFrontend::DefaultGameplayScale();')
    display = graphics / 'graphics_settings_display_panel.cpp'
    add_header(display)
    text = display.read_text()
    marker = '#include "fast/oot3d/render_resolution_policy.h"'
    if marker not in text:
        text = marker + '\n' + text
    if '"Gameplay resolution"' not in text:
        start = text.index('    if (!mRenderScaleEditing)')
        end = text.index('    if(!RetunedFrontend::MobileSettingsPlatform())changed |= ImGui::Checkbox("VSync"', start)
        text = text[:start] + (source / 'render_resolution.cpp.inc').read_text() + '\n' + text[end:]
    display.write_text(text)
