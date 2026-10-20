    void Draw() override {
        if (Oot3d::TakeUnifiedSettingsRequest()) SetVisibility(true);
        if (Oot3d::TakeUnifiedSettingsToggleRequest()) SetVisibility(!IsVisible());
        if (!IsVisible()) {
            Oot3d::GraphicsSettingsRuntime::Instance().SavePending();
            Oot3d::EndGraphicsSettingsPreviews();
            return;
        }
        auto& runtime=Oot3d::GraphicsSettingsRuntime::Instance();
        if(!ImGui::IsAnyItemActive())runtime.SavePending();
        const ImGuiStyle previous=ImGui::GetStyle();
        RetunedFrontend::BlueStyle(ImGui::GetStyle());
        const auto* viewport=ImGui::GetMainViewport();
        ImGui::SetNextWindowPos(viewport->WorkPos,ImGuiCond_Always);
        ImGui::SetNextWindowSize(viewport->WorkSize,ImGuiCond_Always);
        constexpr auto flags=ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoMove|ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoDocking;
        if(ImGui::Begin("Ocarina ReTuned / Settings",nullptr,flags)) {
            ImGui::SetWindowFontScale(1.0f);
            ImGui::TextColored(ImVec4(.39f,.70f,1,1),"Ocarina ReTuned");
            ImGui::SameLine();ImGui::TextUnformatted(" / Settings");
            ImGui::SameLine(std::max(ImGui::GetCursorPosX(),ImGui::GetWindowWidth()-ImGui::GetFontSize()*8));
            if(ImGui::Button("Resume",ImVec2(ImGui::GetFontSize()*6,0)))SetVisibility(false);
#ifdef __APPLE__
            ImGui::TextDisabled("Command + comma: settings");
#else
            ImGui::TextDisabled("Control + comma: settings");
#endif
            ImGui::Separator();
            ImGui::BeginChild("##UnifiedContents");mPanel.Draw();ImGui::EndChild();
        }
        ImGui::End();ImGui::GetStyle()=previous;
        if(!IsVisible())Oot3d::EndGraphicsSettingsPreviews();
    }
