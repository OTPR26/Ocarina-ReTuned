"""Install the blue unified menu and the shared Reframed option bridge."""
from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reframed'))
from apply_native_port import edit

def apply(engine):
    source=Path(__file__).parent
    runtime=engine/'tools/oot3d/native_game_runtime'
    (runtime/'retuned_reframed_settings.h').write_text((source/'reframed_settings.h').read_text())
    include=engine/'runtime/three_ds_recomp/include/fast/oot3d'
    (include/'retuned_blue_style.h').write_text((source/'blue_style.h').read_text())
    graphics=engine/'runtime/three_ds_recomp/src/fast/oot3d/graphics_settings_window.cpp'
    text=graphics.read_text();start=text.index('void GraphicsSettingsPanel::Draw() {');end=text.index('\nvoid GraphicsSettingsPanel::DrawGrassSettings()',start)
    text=text[:start]+(source/'panel_draw.cpp.inc').read_text()+text[end:];graphics.write_text(text)
    edit(graphics,'#include <algorithm>','#include <algorithm>\n#include <atomic>')
    edit(graphics,'namespace Fast::Oot3d {','namespace Fast::Oot3d {\nnamespace { std::atomic<bool> UnifiedSettingsRequested{false}; }\nvoid RequestUnifiedSettings() { UnifiedSettingsRequested.store(true); }\nbool TakeUnifiedSettingsRequest() { return UnifiedSettingsRequested.exchange(false); }')
    edit(include/'graphics_settings_window.h','void DrawDisplayConfirmation();','void DrawDisplayConfirmation();\nvoid RequestUnifiedSettings();\nbool TakeUnifiedSettingsRequest();')
    gui=engine/'runtime/three_ds_recomp/src/fast/Fast3dGui.cpp'
    edit(gui,'#include "fast/oot3d/graphics_settings_window.h"','#include "fast/oot3d/graphics_settings_window.h"\n#include "fast/oot3d/retuned_blue_style.h"')
    text=gui.read_text();start=text.index('    void Draw() override {',text.index('class Oot3dGraphicsSettingsWindow'));end=text.index('\n  protected:',start)
    text=text[:start]+(source/'gui_draw.cpp.inc').read_text()+text[end:];gui.write_text(text)
    edit(gui,'sdlEvent.key.keysym.scancode == SDL_SCANCODE_F1 &&','(sdlEvent.key.keysym.scancode == SDL_SCANCODE_F1 ||\n                         (sdlEvent.key.keysym.scancode == SDL_SCANCODE_COMMA && (sdlEvent.key.keysym.mod & (KMOD_GUI|KMOD_CTRL)))) &&')
    setup=runtime/'oot3d_native_a32_window_setup.cpp'
    edit(setup,'#include "oot3d_native_a32_window_session.h"','#include "oot3d_native_a32_window_session.h"\n#include "retuned_reframed_settings.h"')
    edit(setup, '  if (!launch.TopScreenTextureOverridePackPath.empty()) {\n    const auto fontPath = launch.TopScreenTextureOverridePackPath.parent_path() / "font_coverage.zip";',
         '  {\n    const auto fontPath = launch.UiProfile == Oot3dNativeGame::Oot3dUiProfile::Reframed\n        ? launch.A32ProcessManifestPath.parent_path() / "font_coverage.zip"\n        : launch.TopScreenTextureOverridePackPath.parent_path() / "font_coverage.zip";')
    edit(setup,'  hostConfig.SystemLanguage = languageSettings->SystemId();','  hostConfig.OpenFrontendSettings = [] { Fast::Oot3d::RequestUnifiedSettings(); };\n  hostConfig.SystemLanguage = languageSettings->SystemId();')
    edit(setup,'  // F1 order: the scene lights join Lighting > Lights & Shadows; then',
         '  if (launch.UiProfile == Oot3dNativeGame::Oot3dUiProfile::Reframed)\n    for (const auto* page : {"General", "Reframed controls", "HUD", "Quality of life"})\n      applicationSettingsTabs.push_back(std::make_shared<RetunedFrontend::Panel>(page));\n  // F1 order: the scene lights join Lighting > Lights & Shadows; then')
    edit(setup,'  context = Ship::Context::GetRawInstance();','  context = Ship::Context::GetRawInstance();\n  if (launch.UiProfile == Oot3dNativeGame::Oot3dUiProfile::Reframed) RetunedFrontend::Current().Initialize(launch.A32ProcessManifestPath);')
    frame=runtime/'oot3d_native_a32_window_frame.cpp'
    edit(frame,'#include "oot3d_native_a32_window_session.h"','#include "oot3d_native_a32_window_session.h"\n#include "retuned_reframed_settings.h"')
    edit(frame,'  const auto hidUpdate = hostServices.AdvanceHidToCurrentTick(',
         '  if (launch.UiProfile == Oot3dNativeGame::Oot3dUiProfile::Reframed) RetunedFrontend::Current().Apply(process);\n  const auto hidUpdate = hostServices.AdvanceHidToCurrentTick(')
    edit(runtime/'oot3d_native_a32_ctr_host.h','struct NativeA32CtrHostConfig {','struct NativeA32CtrHostConfig {\n    std::function<void()> OpenFrontendSettings;')
    edit(runtime/'oot3d_native_a32_ctr_host.cpp','    case 0x08: {','    case 0x7E: {\n        event.Name = "OpenFrontendSettings";\n        if (!mConfig.OpenFrontendSettings) return {NativeA32HostAction::Fault};\n        mConfig.OpenFrontendSettings();state.r[0]=kResultSuccess;event.Handled=true;\n        mSvcEvents.push_back(std::move(event));return {NativeA32HostAction::Resume};\n    }\n    case 0x08: {')
    edit(runtime/'oot3d_native_controls_settings_panel.cpp', '"ZL", "ZR", "Select", "Start",', '"ZL", "ZR", "Inventory / pause", "Save menu",')
    controls_panel=runtime/'oot3d_native_controls_settings_panel.cpp'
    edit(controls_panel,
         '          // A single scrolling body; persistence never scrolls with the fields.\n          ImGui::BeginChild(label, ImVec2(0.0F, std::max(\n              1.0F, ImGui::GetContentRegionAvail().y - ImGui::GetFrameHeightWithSpacing() * 3.0F)));\n          draw();\n          ImGui::EndChild();',
         '          // The unified page owns scrolling, including every binding row.\n          draw();')
    controls=runtime/'oot3d_native_control_config.cpp'
    edit(controls,'SetKeyboardBinding(config, NativeControlAction::Select,\n                     NativeKeyboardKey::Tab, NativeKeyboardKey::Backspace);\n  SetKeyboardBinding(config, NativeControlAction::Start,\n                     NativeKeyboardKey::Enter);','SetKeyboardBinding(config, NativeControlAction::Select,\n                     NativeKeyboardKey::Enter);\n  SetKeyboardBinding(config, NativeControlAction::Start,\n                     NativeKeyboardKey::Tab, NativeKeyboardKey::Backspace);')
    edit(controls,'SetGamepadBinding(config, NativeControlAction::Select,\n                    NativeGamepadButton::Back);\n  SetGamepadBinding(config, NativeControlAction::Start,\n                    NativeGamepadButton::Start);','SetGamepadBinding(config, NativeControlAction::Select,\n                    NativeGamepadButton::Start);\n  SetGamepadBinding(config, NativeControlAction::Start,\n                    NativeGamepadButton::Back);')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('engine',type=Path);apply(p.parse_args().engine)
