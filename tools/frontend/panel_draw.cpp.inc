void GraphicsSettingsPanel::Draw() {

    static int page=0;
    if(RetunedFrontend::RequestedSettingsPage>=0){page=RetunedFrontend::RequestedSettingsPage;RetunedFrontend::RequestedSettingsPage=-1;}
    const char* pages[]={"General","Controls","HUD","Quality of life","Graphics","Lighting","Textures","Save states","Language","Advanced","Touch controls"};
    const float font=ImGui::GetFontSize();
    ImGui::BeginChild("##Navigation",ImVec2(RetunedFrontend::NavigationWidth(ImGui::GetContentRegionAvail().x,font),0),true);
    for(int i:{0,1,10,2,3,4,5,6,7,8,9}){
        if(RetunedFrontend::MobileSettingsPlatform() && i==9)continue;
        if(!RetunedFrontend::TouchPlatform() && i==10)continue;
        const bool selected=page==i;
        if(selected)ImGui::PushStyleColor(ImGuiCol_Button,ImGui::GetStyleColorVec4(ImGuiCol_Header));
        if(ImGui::Button(pages[i],ImVec2(-1,std::max(font*2.5f,44.f))))page=i;
        if(selected)ImGui::PopStyleColor();
    }
    ImGui::EndChild();ImGui::SameLine();
    ImGui::BeginChild("##SettingsPage",ImVec2(0,0),true);
    ImGui::TextColored(ImGui::GetStyleColorVec4(ImGuiCol_CheckMark),"%s",pages[page]);ImGui::Separator();ImGui::Spacing();
    auto drawTabs=[&](const char* label){for(const auto& tab:SnapshotPanelTabs())if(std::string_view(tab->Label())==label){ImGui::PushID(tab->Label());tab->Draw();ImGui::PopID();}};
    ImGui::PushItemWidth(std::min(ImGui::GetContentRegionAvail().x*.58f,font*18));
    switch(page){
      case 0:
        if(RetunedFrontend::MobileSettingsPlatform()) {
          auto config=Ship::Context::GetRawInstance()->GetConfig();
          ImGui::SliderFloat("Menu size",&RetunedFrontend::MenuSize,.8f,1.25f,"%.2fx");
          if(ImGui::IsItemDeactivatedAfterEdit()){config->SetFloat("Interface.Scale",RetunedFrontend::MenuSize);config->Save();}
          ImGui::Spacing();
        }
        drawTabs("General");break;
      case 1:
        if(ImGui::CollapsingHeader("Game control options")){drawTabs("Reframed controls");ImGui::Separator();}
        drawTabs("Controls");break;
      case 2:drawTabs("HUD");break;
      case 3:drawTabs("Quality of life");break;
      case 4:
        if(!RetunedFrontend::MobileSettingsPlatform())DrawPresetSelector();DrawSettingsSections({&GraphicsSettingsPanel::DrawDisplaySettings,&GraphicsSettingsPanel::DrawAntialiasingSettings,&GraphicsSettingsPanel::DrawMotionSettings});break;
      case 5:{std::vector<std::shared_ptr<GraphicsSettingsPanelTab>> lighting;for(const auto& tab:SnapshotPanelTabs())if(tab->Group() && std::string_view(tab->Group())==kLightingSettingsGroup)lighting.push_back(tab);DrawLightingTab(lighting);break;}
      case 6:DrawTextureSettings();break;
      case 7:drawTabs("Save states");break;
      case 8:drawTabs("Language");break;
      case 10:RetunedFrontend::DrawTouchSettings();break;
      case 9:DrawGrassSettings();ImGui::Separator();DrawMaterialsTab();break;
    }
    ImGui::PopItemWidth();ImGui::EndChild();
}
