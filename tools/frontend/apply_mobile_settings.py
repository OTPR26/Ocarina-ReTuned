"""Keep mobile settings focused on controls the fullscreen app can apply."""
from pathlib import Path
from apply_native_port import edit

def apply(engine):
    engine=Path(engine)
    graphics=engine/'runtime/three_ds_recomp/src/fast/oot3d'
    runtime=engine/'tools/oot3d/native_game_runtime'
    def header(path):
        marker='#include "fast/oot3d/retuned_interface_metrics.h"'
        if marker not in path.read_text():path.write_text(marker+'\n'+path.read_text())
    display=graphics/'graphics_settings_display_panel.cpp';header(display)
    s=display.read_text()
    if '// Desktop display controls' not in s:
        start=s.index('    const auto observed =')
        end=s.index('    if (!mRenderScaleEditing)',start)
        s=s[:start]+'    // Desktop display controls\n    if(!RetunedFrontend::MobileSettingsPlatform()) {\n'+s[start:end]+'    }\n'+s[end:]
        s=s.replace('    changed |= ImGui::Checkbox("VSync", &settings.VSync);','    if(!RetunedFrontend::MobileSettingsPlatform())changed |= ImGui::Checkbox("VSync", &settings.VSync);')
        display.write_text(s)
    widgets=engine/'runtime/three_ds_recomp/include/fast/oot3d/settings_panel_widgets.h';header(widgets)
    edit(widgets,'        ImGui::BeginDisabled(!supported);','        if(RetunedFrontend::MobileSettingsPlatform() && !supported && current!=option)continue;\n        ImGui::BeginDisabled(!supported);')
    textures=graphics/'azahar_texture_pack_panel.cpp';header(textures)
    header_marker='#include "fast/oot3d/retuned_texture_folder.h"'
    text=textures.read_text()
    style='#include "fast/oot3d/retuned_blue_style.h"'
    if style not in text:textures.write_text(style+'\n'+text)
    text=textures.read_text()
    if header_marker not in text:text=header_marker+'\n'+text
    picker_marker='#include "fast/oot3d/retuned_desktop_texture_picker.h"'
    if picker_marker not in text:text=picker_marker+'\n'+text
    start=text.index('bool DrawAzaharTexturePackPanel(')
    body=text.index('{',start)+1
    end=text.index('\n    SynchronizeDirectoryInputs(settings, state);',body)+1
    text=text[:body]+'\n'+Path(__file__).with_name('mobile_textures.cpp.inc').read_text()+'''#if !defined(__SWITCH__) && !defined(__IOS__) && !defined(__ANDROID__)
    if(RetunedFrontend::DrawDesktopTexturePicker(settings.LoadDirectory)) {
        settings.LoadCustomTextures=true;
        SynchronizeDirectoryInputs(settings,state);
        return true;
    }
#endif
'''+text[end:]
    textures.write_text(text)
    loader=graphics/'azahar_texture_pack.cpp'
    text=loader.read_text()
    if header_marker not in text:loader.write_text(header_marker+'\n'+text)
    edit(loader,'std::vector<uint8_t> ReadBinaryFile(const std::filesystem::path& path) {',
         'std::vector<uint8_t> ReadBinaryFile(const std::filesystem::path& path) {\n    if(RetunedFrontend::TextureFolders.Read && RetunedFrontend::IsTextureDocument(path.string()))return RetunedFrontend::ReadTextureDocument(path.string());')
    frame=engine/'runtime/three_ds_recomp/src/fast/backends/gfx_vulkan_frame.cpp'
    for field in ('LoadDirectory','DumpDirectory'):
        old='graphicsSettings.TexturePacks.Azahar.'+field+','
        edit(frame,old,'std::filesystem::u8path(graphicsSettings.TexturePacks.Azahar.'+field+'),')
    controls=runtime/'oot3d_native_controls_settings_panel.cpp';header(controls)
    edit(controls,'  void DrawDevices() {','''  void DrawDevices() {
    if(RetunedFrontend::MobileSettingsPlatform()) {
      if(RetunedFrontend::Toggle("Use connected controller",&mControlDraft.ControllerEnabled))MarkCustom(mControlDraft,mControlDirty);
      return;
    }''')
    states=runtime/'oot3d_savestate_panel.cpp';header(states)
    for desktop,mobile in [('Save state (F5)','Save state'),('Save state + settings (Shift+F5)','Save state + settings'),('Load last state (F8)','Load last state'),('Load last state + settings (Shift+F8)','Load last state + settings')]:
        edit(states,'ImGui::Button("'+desktop+'")','ImGui::Button(RetunedFrontend::MobileSettingsPlatform()?"'+mobile+'":"'+desktop+'")')
    edit(states,'  void DrawFolder(bool fixedSlot) {','''  void DrawFolder(bool fixedSlot) {
    if(RetunedFrontend::MobileSettingsPlatform()){ImGui::TextWrapped("Save states are stored in this app.");return;}''')
    edit(states,'    if (ImGui::Button("Choose a state file...")) {','    if (!RetunedFrontend::MobileSettingsPlatform() && ImGui::Button("Choose a state file...")) {')
    s=states.read_text().replace('    ImGui::SameLine();','    if(!RetunedFrontend::MobileSettingsPlatform())ImGui::SameLine();');states.write_text(s)
    edit(states,'    ImGui::TextDisabled("Select a state to make it the one F8 loads.");','    ImGui::TextWrapped("Select a state to use with Load last state.");')
    from apply_render_resolution import apply as apply_resolution
    apply_resolution(engine)
    from apply_texture_memory import apply as apply_memory
    apply_memory(engine)
