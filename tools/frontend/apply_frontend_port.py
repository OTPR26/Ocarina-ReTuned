"""Install the blue unified menu and the shared Reframed option bridge."""
from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reframed'))
from apply_native_port import edit

def apply(engine):
    source=Path(__file__).parent
    runtime=engine/'tools/oot3d/native_game_runtime'
    (runtime/'retuned_reframed_settings.h').write_text((source/'reframed_settings.h').read_text())
    (runtime/'retuned_ocarina_lifecycle.h').write_text((source/'ocarina_lifecycle.h').read_text())
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
    edit(runtime/'oot3d_native_controls_settings_panel.cpp', '"ZL", "ZR", "Select", "Start",', '"ZL", "ZR", "Inventory / pause", "Settings",')
    controls_panel=runtime/'oot3d_native_controls_settings_panel.cpp'
    panel=controls_panel.read_text()
    body=panel.index('  void Draw() override {')
    marker='    ImGui::TextDisabled("Select a binding' if '    ImGui::TextDisabled("Select a binding' in panel else '    DrawProfile();'
    start=panel.index(marker,body)
    end=panel.index('    DrawBindingCapture();',start)
    panel=panel[:start]+(source/'controls_sections.cpp.inc').read_text()+panel[end:]
    start=panel.index('  void DrawBindings()');end=panel.index('  void DrawBindingGroup(',start)
    panel=panel[:start]+(source/'bindings_draw.cpp.inc').read_text()+panel[end:]
    start=panel.index('  void DrawBindingGroup(');end=panel.index('\n  void DrawAnalog()',start)
    panel=panel[:start]+(source/'binding_rows.cpp.inc').read_text()+panel[end:]
    controls_panel.write_text(panel)
    for styled in (controls_panel,graphics):
        text=styled.read_text()
        if '#include "fast/oot3d/retuned_blue_style.h"' not in text:
            text='#include "fast/oot3d/retuned_blue_style.h"\n'+text
        styled.write_text(text.replace('ImGui::Checkbox(', 'RetunedFrontend::Toggle('))
    font=(source.parents[1]/'resources/fonts/InterfaceSans-Regular.ttf').read_bytes()
    font_header=include/'retuned_interface_font.h'
    font_header.write_text('#pragma once\nnamespace RetunedFrontend { inline unsigned char InterfaceFont[] = {\n'+
        ','.join(str(byte) for byte in font)+'\n}; }\n')
    gui_core=engine/'runtime/three_ds_recomp/src/ship/window/gui/Gui.cpp'
    edit(gui_core,'#include "ship/window/gui/Gui.h"','#include "ship/window/gui/Gui.h"\n#include "fast/oot3d/retuned_interface_font.h"')
    edit(gui_core,'    mImGuiIo->Fonts->AddFontDefault();',
         '    ImFontConfig interfaceFont; interfaceFont.FontDataOwnedByAtlas=false;\n    interfaceFont.OversampleH=2; interfaceFont.OversampleV=2;\n    mImGuiIo->Fonts->AddFontFromMemoryTTF(RetunedFrontend::InterfaceFont,sizeof(RetunedFrontend::InterfaceFont),40.f,&interfaceFont);\n    mImGuiIo->FontGlobalScale=.5f;')
    edit(gui_core,'    float baseFontSize = 13.0f;','    float baseFontSize = 40.0f;')
    (include/'retuned_texture_aliases.h').write_text((source/'texture_aliases.h').read_text())
    (runtime/'retuned_load_texture_aliases.h').write_text((source/'load_texture_aliases.h').read_text())
    texture_header=engine/'runtime/three_ds_recomp/include/oot3d/renderer/azahar_texture_pack.h'
    texture_cpp=engine/'runtime/three_ds_recomp/src/fast/oot3d/azahar_texture_pack.cpp'
    edit(texture_header,'#pragma once','#pragma once\n#include "fast/oot3d/retuned_texture_aliases.h"')
    edit(texture_header,'    void Configure(AzaharTexturePackConfiguration configuration);','    void Configure(AzaharTexturePackConfiguration configuration);\n    void SetHashAliases(std::vector<TextureHashAlias> aliases);')
    edit(texture_cpp,'    void Configure(AzaharTexturePackConfiguration configuration) {',
         '    void SetHashAliases(std::vector<TextureHashAlias> aliases) {\n        std::scoped_lock lock(mMutex);\n        if(mHashAliases==aliases)return;\n        mHashAliases=std::move(aliases);\n        if(mConfigured)RequestRebuildLocked();\n    }\n    void Configure(AzaharTexturePackConfiguration configuration) {')
    edit(texture_cpp,'    PackState mPack;','    PackState mPack;\n    std::vector<TextureHashAlias> mHashAliases;')
    edit(texture_cpp,'            index = IndexTexturePack(loadDirectory, pack, unsupported, materials, &error);',
         '            index = IndexTexturePack(loadDirectory, pack, unsupported, materials, &error);\n            {std::scoped_lock lock(mMutex);ApplyTextureHashAliases(index,mHashAliases,pack.UseNewHash);}')
    edit(texture_cpp,'void AzaharTexturePackRuntime::Reload() {',
         'void AzaharTexturePackRuntime::SetHashAliases(std::vector<TextureHashAlias> aliases) { mImpl->SetHashAliases(std::move(aliases)); }\n\nvoid AzaharTexturePackRuntime::Reload() {')
    edit(setup,'#include "retuned_reframed_settings.h"','#include "retuned_reframed_settings.h"\n#include "retuned_load_texture_aliases.h"')
    edit(setup,'  hostConfig.WritableHidSharedMemory = launch.UiProfile == Oot3dNativeGame::Oot3dUiProfile::Reframed;',
         '  if(launch.UiProfile == Oot3dNativeGame::Oot3dUiProfile::Reframed)RetunedFrontend::LoadTextureAliases(launch.A32ProcessManifestPath);\n  hostConfig.WritableHidSharedMemory = launch.UiProfile == Oot3dNativeGame::Oot3dUiProfile::Reframed;')
    (include/'retuned_tab_hints.h').write_text((source/'tab_hints.h').read_text())
    (include/'retuned_settings_button.h').write_text((source/'settings_button.h').read_text())
    edit(frame,'#include "retuned_reframed_settings.h"','#include "retuned_reframed_settings.h"\n#include "fast/oot3d/retuned_settings_button.h"')
    edit(gui,'#include "fast/oot3d/retuned_blue_style.h"','#include "fast/oot3d/retuned_blue_style.h"\n#include "fast/oot3d/retuned_tab_hints.h"')
    edit(gui,'void Fast3dGui::DrawMenu() {\n    Ship::Gui::DrawMenu();',
         'void Fast3dGui::DrawMenu() {\n    Ship::Gui::DrawMenu();\n    if(!GetAnyGuiWindowVisible())RetunedFrontend::DrawTabHints();')
    host=runtime/'oot3d_native_a32_ctr_host.cpp'
    edit(runtime/'oot3d_native_a32_ctr_host.h','    std::function<void()> OpenFrontendSettings;','    std::function<void()> OpenFrontendSettings;\n    std::function<void()> PublishPauseTabHints;')
    edit(setup,'#include "retuned_load_texture_aliases.h"','#include "retuned_load_texture_aliases.h"\n#include "fast/oot3d/retuned_tab_hints.h"')
    edit(setup,'  hostConfig.OpenFrontendSettings = [] { Fast::Oot3d::RequestUnifiedSettings(); };','  hostConfig.OpenFrontendSettings = [] { Fast::Oot3d::RequestUnifiedSettings(); };\n  hostConfig.PublishPauseTabHints = [] { RetunedFrontend::PublishTabHints(); };')
    edit(host,'    case 0x7E: {','    case 0x7D: {\n        if(mConfig.PublishPauseTabHints)mConfig.PublishPauseTabHints();state.r[0]=kResultSuccess;\n        event.Name="ShowPauseTabHints";event.Handled=true;mSvcEvents.push_back(std::move(event));\n        return {NativeA32HostAction::Resume};\n    }\n    case 0x7E: {')
    edit(runtime/'oot3d_native_a32_window_session.h','  bool quickSaveKeyWasDown', '  bool reframedSettingsHeld=false;\n  bool quickSaveKeyWasDown')
    edit(frame,'  if (physicalInputFrame.Exit || devLabQuit) {',
         '  if(launch.UiProfile == Oot3dNativeGame::Oot3dUiProfile::Reframed) {\n    const auto settingsButton=Oot3dNativeGame::NativeA32HidButtonMask(Oot3dNativeGame::NativeA32HidButton::Start);\n    if(RetunedFrontend::RouteSettingsButton(physicalInputFrame.Hid.Buttons,settingsButton,reframedSettingsHeld,hostGuiVisible))Fast::Oot3d::RequestUnifiedSettings();\n  }\n  if (physicalInputFrame.Exit || devLabQuit) {')
    edit(controls_panel,'"Inventory / pause", "Save menu",','"Inventory / pause", "Settings",')
    controls=runtime/'oot3d_native_control_config.cpp'
    edit(controls,'SetKeyboardBinding(config, NativeControlAction::Select,\n                     NativeKeyboardKey::Tab, NativeKeyboardKey::Backspace);\n  SetKeyboardBinding(config, NativeControlAction::Start,\n                     NativeKeyboardKey::Enter);','SetKeyboardBinding(config, NativeControlAction::Select,\n                     NativeKeyboardKey::Enter);\n  SetKeyboardBinding(config, NativeControlAction::Start,\n                     NativeKeyboardKey::Tab, NativeKeyboardKey::Backspace);')
    edit(controls,'SetGamepadBinding(config, NativeControlAction::Select,\n                    NativeGamepadButton::Back);\n  SetGamepadBinding(config, NativeControlAction::Start,\n                    NativeGamepadButton::Start);','SetGamepadBinding(config, NativeControlAction::Select,\n                    NativeGamepadButton::Start);\n  SetGamepadBinding(config, NativeControlAction::Start,\n                    NativeGamepadButton::Back);')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('engine',type=Path);apply(p.parse_args().engine)
