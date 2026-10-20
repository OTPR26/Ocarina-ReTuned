void GraphicsSettingsPanel::Draw() {

    static int page=0;
    const char* pages[]={"General","Controls","HUD","Quality of life","Graphics","Lighting","Textures","Save states","Language","Advanced"};
    const float font=ImGui::GetFontSize();
    ImGui::BeginChild("##Navigation",ImVec2(std::clamp(ImGui::GetContentRegionAvail().x*.23f,font*10,font*15),0),true);
    for(int i=0;i<10;++i){
        const bool selected=page==i;
        if(selected)ImGui::PushStyleColor(ImGuiCol_Button,ImGui::GetStyleColorVec4(ImGuiCol_Header));
        if(ImGui::Button(pages[i],ImVec2(-1,font*2.5f)))page=i;
        if(selected)ImGui::PopStyleColor();
    }
    ImGui::EndChild();ImGui::SameLine();
    ImGui::BeginChild("##SettingsPage",ImVec2(0,0),true);
    ImGui::TextColored(ImVec4(.39f,.70f,1,1),"%s",pages[page]);ImGui::Separator();ImGui::Spacing();
    auto drawTabs=[&](const char* label){for(const auto& tab:SnapshotPanelTabs())if(std::string_view(tab->Label())==label){ImGui::PushID(tab->Label());tab->Draw();ImGui::PopID();}};
    ImGui::PushItemWidth(std::min(ImGui::GetContentRegionAvail().x,font*26));
    switch(page){
      case 0:drawTabs("General");break;
      case 1:
        if(ImGui::CollapsingHeader("Game control options")){drawTabs("Reframed controls");ImGui::Separator();}
        drawTabs("Controls");break;
      case 2:drawTabs("HUD");break;
      case 3:drawTabs("Quality of life");break;
      case 4:
        DrawPresetSelector();DrawSettingsSections({&GraphicsSettingsPanel::DrawDisplaySettings,&GraphicsSettingsPanel::DrawAntialiasingSettings,&GraphicsSettingsPanel::DrawMotionSettings});break;
      case 5:{std::vector<std::shared_ptr<GraphicsSettingsPanelTab>> lighting;for(const auto& tab:SnapshotPanelTabs())if(tab->Group() && std::string_view(tab->Group())==kLightingSettingsGroup)lighting.push_back(tab);DrawLightingTab(lighting);break;}
      case 6:DrawTextureSettings();break;
      case 7:drawTabs("Save states");break;
      case 8:drawTabs("Language");break;
      case 9:DrawGrassSettings();ImGui::Separator();DrawMaterialsTab();break;
    }
    ImGui::PopItemWidth();ImGui::EndChild();
}
