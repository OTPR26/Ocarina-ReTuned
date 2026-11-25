"""Add bounded Android graphics-transition diagnostics to the staged engine."""
from pathlib import Path


def apply(engine):
    engine = Path(engine)
    include = engine / 'runtime/three_ds_recomp/include/fast/oot3d'
    include.mkdir(parents=True, exist_ok=True)
    (include / 'retuned_graphics_settings_trace.h').write_text(
        Path(__file__).with_name('graphics_settings_trace.h').read_text())
    runtime = engine / 'runtime/three_ds_recomp/src/fast/oot3d/graphics_settings_runtime.cpp'
    text = runtime.read_text()
    header = '#include "fast/oot3d/retuned_graphics_settings_trace.h"\n'
    if header not in text:
        text = header + text
    old = '''GraphicsSettingsValidation GraphicsSettingsRuntime::Apply(GraphicsSettings candidate, bool persist) {
    std::scoped_lock lock(mMutex);'''
    new = '''GraphicsSettingsValidation GraphicsSettingsRuntime::Apply(GraphicsSettings candidate, bool persist) {
    RetunedFrontend::GraphicsSettingsTrace trace("apply");
    std::scoped_lock lock(mMutex);
    trace.Mark("lock-acquired");'''
    if new not in text:
        if old not in text:
            raise RuntimeError('Graphics settings Apply signature changed')
        text = text.replace(old, new, 1)
    old = 'bool GraphicsSettingsRuntime::PersistCurrentLocked() {'
    new = old + '\n    RetunedFrontend::GraphicsSettingsTrace trace("persist");'
    if new not in text:
        if old not in text:
            raise RuntimeError('Graphics persistence signature changed')
        text = text.replace(old, new, 1)
    runtime.write_text(text)

    frame = engine / 'tools/oot3d/native_game_runtime/oot3d_native_a32_window_frame.cpp'
    text = frame.read_text()
    if header not in text:
        text = header + text
    replacements = (
        ('presentationPacingPolicy, requestedPresentationPolicy)) {',
         'presentationPacingPolicy, requestedPresentationPolicy)) {\n    RetunedFrontend::GraphicsSettingsTrace policyTrace("presentation-submit");'),
        ('compositionModeChanged] {\n    frameCompositionPolicy',
         'compositionModeChanged] {\n    RetunedFrontend::GraphicsSettingsTrace policyTrace("presentation-render");\n    frameCompositionPolicy'),
    )
    for old, new in replacements:
        if new not in text:
            if old not in text:
                raise RuntimeError('Presentation policy transition changed')
            text = text.replace(old, new, 1)
    frame.write_text(text)
