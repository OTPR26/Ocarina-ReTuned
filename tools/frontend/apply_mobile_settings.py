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
    edit(textures,'    SynchronizeDirectoryInputs(settings, state);','''    if(RetunedFrontend::MobileSettingsPlatform()) {
        const bool changed=ImGui::Checkbox("Load custom textures",&settings.LoadCustomTextures);
        auto& packs=::Oot3d::Renderer::AzaharTexturePackRuntime::Instance();
        if(ImGui::Button("Reload textures"))packs.Reload();
        const auto status=packs.Snapshot();
        if(status.IndexPending)ImGui::TextWrapped("Finding textures...");
        else if(status.IndexedTextures==0)ImGui::TextWrapped("No texture pack found. Add a pack during app setup.");
        else ImGui::TextWrapped("%zu textures available; %zu loaded",status.IndexedTextures,status.LoadedTextures);
        if(status.PendingLoads)ImGui::Text("Loading: %zu",status.PendingLoads);
        if(status.FailedLoads)ImGui::Text("Could not load: %zu",status.FailedLoads);
        if(!status.LastError.empty())ImGui::TextWrapped("%s",status.LastError.c_str());
        return changed;
    }
    SynchronizeDirectoryInputs(settings, state);''')
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
