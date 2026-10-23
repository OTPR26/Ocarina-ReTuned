void GraphicsSettingsPanel::Draw() {
    using RetunedFrontend::SettingsPage;
    static auto page=SettingsPage::General;
    const bool mobile=RetunedFrontend::MobileSettingsPlatform(),touch=RetunedFrontend::TouchPlatform();
    if(RetunedFrontend::RequestedSettingsPage>=0){
        const auto requested=static_cast<SettingsPage>(RetunedFrontend::RequestedSettingsPage);
        for(const auto& category:RetunedFrontend::SettingsCategories)
            if(category.Page==requested && RetunedFrontend::CategoryVisible(requested,mobile,touch))page=requested;
        RetunedFrontend::RequestedSettingsPage=-1;
    }
    static auto previousPage=page;
    const float font=ImGui::GetFontSize();
    ImGui::BeginChild("##Navigation",ImVec2(RetunedFrontend::NavigationWidth(ImGui::GetContentRegionAvail().x,font),0),true);
    float selectedCategoryY=0;
    for(const auto& category:RetunedFrontend::SettingsCategories){
        if(!RetunedFrontend::CategoryVisible(category.Page,mobile,touch))continue;
        const bool selected=page==category.Page;
        if(selected)ImGui::PushStyleColor(ImGuiCol_Button,ImGui::GetStyleColorVec4(ImGuiCol_Header));
        const bool activated=ImGui::Button(category.Label,ImVec2(-1,std::max(font*2.5f,44.f)));
        if(selected || activated){
            RetunedFrontend::SettingsNav.SelectedCategory=ImGui::GetItemID();
            selectedCategoryY=ImGui::GetItemRectMin().y-ImGui::GetWindowPos().y+font;
        }
        if(activated){page=category.Page;RetunedFrontend::SettingsNav.ActivateCategory(ImGui::GetItemID());}
        if(selected)ImGui::PopStyleColor();
    }
    RetunedFrontend::SettingsNav.CategoriesDrawn(selectedCategoryY);
    ImGui::EndChild();ImGui::SameLine();
    if(page!=previousPage){ImGui::SetNextWindowScroll({0,0});previousPage=page;}
    ImGui::BeginChild("##SettingsPage",ImVec2(0,0),true);
    RetunedFrontend::SettingsNav.PageBegun();
    for(const auto& category:RetunedFrontend::SettingsCategories)if(category.Page==page){
        ImGui::TextColored(ImGui::GetStyleColorVec4(ImGuiCol_CheckMark),"%s",category.Label);
        ImGui::TextWrapped("%s",category.Description);
    }
    ImGui::Separator();ImGui::Spacing();
    auto drawTabs=[&](const char* label){for(const auto& tab:SnapshotPanelTabs())if(std::string_view(tab->Label())==label){ImGui::PushID(tab->Label());tab->Draw();ImGui::PopID();}};
    ImGui::PushItemWidth(std::min(ImGui::GetContentRegionAvail().x*.58f,font*18));
    switch(page){
      case SettingsPage::General: {
        drawTabs("Language");ImGui::Spacing();
#ifdef __APPLE__
        ImGui::SeparatorText("iCloud saves");
        bool cloudEnabled=RetunedSaveSyncEnabled();
        if(RetunedFrontend::Toggle("Sync game saves with iCloud",&cloudEnabled))RetunedSaveSyncSetEnabled(cloudEnabled);
        char cloudStatus[384];RetunedSaveSyncStatus(cloudStatus,sizeof(cloudStatus));
        ImGui::TextWrapped("%s",cloudStatus);
        if(cloudEnabled && ImGui::Button("Sync now"))RetunedSaveSyncRequest();
        if(RetunedSaveSyncConflict()) {
            ImGui::TextWrapped("Your devices have different progress. Previous saves are backed up before replacement.");
            ImGui::BeginDisabled(!RetunedFrontend::StartupVisible);
            if(ImGui::Button("Use this device's saves"))RetunedSaveSyncResolve(false);
            if(ImGui::Button("Use iCloud saves"))RetunedSaveSyncResolve(true);
            ImGui::EndDisabled();
            if(!RetunedFrontend::StartupVisible)ImGui::TextWrapped("Restart to the app startup screen to choose saves safely.");
        }
        ImGui::TextWrapped("Only game saves sync. Graphics, controls and texture folders stay on this device.");
#endif
        auto config=Ship::Context::GetRawInstance()->GetConfig();
        ImGui::SeparatorText("Menu");
        ImGui::SliderFloat("Menu size",&RetunedFrontend::MenuSize,.8f,1.25f,"%.2fx");
        bool saveSize=ImGui::IsItemDeactivatedAfterEdit();
        if(ImGui::Button("Reset menu size")){RetunedFrontend::MenuSize=1.f;saveSize=true;}
        if(saveSize){config->SetFloat("Interface.Scale",RetunedFrontend::MenuSize);config->Save();}
        if(mobile && ImGui::CollapsingHeader("Save states"))drawTabs("Save states");
        break;
      }
      case SettingsPage::Controls:
        if(ImGui::CollapsingHeader("Game control options")){drawTabs("Reframed controls");ImGui::Separator();}
        drawTabs("Controls");break;
      case SettingsPage::Touch:RetunedFrontend::DrawTouchSettings();break;
      case SettingsPage::Graphics:
        if(!mobile)DrawPresetSelector();
        DrawSettingsSections({&GraphicsSettingsPanel::DrawMotionSettings});
        drawTabs("Camera");
        DrawSettingsSections({&GraphicsSettingsPanel::DrawDisplaySettings,&GraphicsSettingsPanel::DrawAntialiasingSettings});
        ImGui::SeparatorText("Custom textures");DrawTextureSettings();
        if(ImGui::CollapsingHeader("Lighting")){
            std::vector<std::shared_ptr<GraphicsSettingsPanelTab>> lighting;
            for(const auto& tab:SnapshotPanelTabs())if(tab->Group() && std::string_view(tab->Group())==kLightingSettingsGroup)lighting.push_back(tab);
            DrawLightingTab(lighting);
        }
        break;
      case SettingsPage::Audio: {
        auto config=Ship::Context::GetRawInstance()->GetConfig();
        bool muted=Retuned::OutputMuted.load();
        if(RetunedFrontend::Toggle("Mute audio",&muted)){
            Retuned::OutputMuted=muted;config->SetBool("Audio.Muted",muted);config->Save();
        }
        float volume=Retuned::OutputVolume.load()*100.f;
        if(ImGui::SliderFloat("Volume",&volume,0.f,100.f,"%.0f%%"))Retuned::OutputVolume=volume/100.f;
        if(ImGui::IsItemDeactivatedAfterEdit()){config->SetFloat("Audio.Volume",Retuned::OutputVolume.load());config->Save();}
        ImGui::TextWrapped("Controls all game sound. Your device volume remains separate.");
        break;
      }
      case SettingsPage::Hud: {
        ImGui::SeparatorText("Dialogue");
        auto config=Ship::Context::GetRawInstance()->GetConfig();
        int weight=config->GetString("Interface.DialogueFontWeight","bold")=="regular" ? 0 : 1;
        ImGui::BeginDisabled(!RetunedFrontend::DialogueFontChoicesAvailable);
        if(ImGui::Combo("Dialogue font",&weight,"Regular\0Bold\0")) {
            config->SetString("Interface.DialogueFontWeight",weight==0 ? "regular" : "bold");
            config->Save();
        }
        ImGui::EndDisabled();
        if(!RetunedFrontend::DialogueFontChoicesAvailable)
            ImGui::TextWrapped("Update game setup to enable both dialogue fonts.");
        else if(RetunedFrontend::ActiveDialogueFontWeight!=(weight==0 ? "regular" : "bold"))
            ImGui::TextWrapped("Restart the app to apply your dialogue font. Save your game first.");
        else ImGui::TextWrapped("Regular and Bold use the same sharp dialogue rendering.");
        ImGui::Separator();drawTabs("HUD");break;
      }
      case SettingsPage::QualityOfLife:
        ImGui::SeparatorText("Link movement");drawTabs("Quality of life");break;
      case SettingsPage::About:
        ImGui::TextUnformatted("Ocarina ReTuned");ImGui::TextDisabled("0.1.0 Preview");
        ImGui::Spacing();ImGui::TextWrapped("Ocarina of Time 3D with the Reframed single-screen HUD.");
        ImGui::SeparatorText("Contributors");
        ImGui::TextWrapped("Upstream engine credits: TriAevum by coccofresco. Uses libultraship, SDL, Dear ImGui and MoltenVK on Apple devices. Interface fonts: Liberation Sans (SIL Open Font License).");
        break;
      case SettingsPage::SaveStates:drawTabs("Save states");break;
      case SettingsPage::SaveFiles:
#ifdef __ANDROID__
        RetunedFrontend::DrawAndroidSaveFiles();
#endif
        break;
      case SettingsPage::Advanced:DrawGrassSettings();ImGui::Separator();DrawMaterialsTab();break;
    }
    ImGui::PopItemWidth();ImGui::EndChild();
}
