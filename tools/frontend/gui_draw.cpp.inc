    void Draw() override {
        if (Oot3d::TakeUnifiedSettingsRequest()) SetVisibility(true);
        if (Oot3d::TakeUnifiedSettingsToggleRequest()) SetVisibility(!IsVisible());
        if (!IsVisible()) {
            Oot3d::GraphicsSettingsRuntime::Instance().SavePending();
            Oot3d::EndGraphicsSettingsPreviews();
            return;
        }
        RetunedFrontend::SettingsNav.Begin(RetunedFrontend::TelevisionPlatform());
        auto& runtime=Oot3d::GraphicsSettingsRuntime::Instance();
        if(!ImGui::IsAnyItemActive())runtime.SavePending();
        const ImGuiStyle previous=ImGui::GetStyle();
        const float previousFontScale=ImGui::GetIO().FontGlobalScale;
        RetunedFrontend::BlueStyle(ImGui::GetStyle());
        const auto* viewport=ImGui::GetMainViewport();
        const float scale=RetunedFrontend::MenuScale(viewport->WorkSize.y);
        ImGui::GetIO().FontGlobalScale=RetunedFrontend::InterfaceFontScale(scale);
        ImGui::GetStyle().ScaleAllSizes(scale);
        ImGui::PushFont(ImGui::GetFont());
        ImGui::SetNextWindowPos(viewport->WorkPos,ImGuiCond_Always);
        ImGui::SetNextWindowSize(viewport->WorkSize,ImGuiCond_Always);
        if(RetunedFrontend::MobileSettingsPlatform()){
            ImGui::GetStyle().FramePadding.y=std::max(ImGui::GetStyle().FramePadding.y,12.f*scale);
            ImGui::GetStyle().WindowPadding.x=std::max(ImGui::GetStyle().WindowPadding.x,40.f*scale);
        }
        constexpr auto flags=ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoMove|ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoDocking;
        if(ImGui::Begin("Ocarina ReTuned / Settings",nullptr,flags)) {
            ImGui::SetWindowFontScale(1.0f);
            ImGui::TextColored(ImGui::GetStyleColorVec4(ImGuiCol_CheckMark),"Ocarina ReTuned");
            ImGui::SameLine();ImGui::TextUnformatted(" / Settings");
            ImGui::SameLine(std::max(ImGui::GetCursorPosX(),ImGui::GetWindowWidth()-ImGui::GetFontSize()*8));
            if(ImGui::Button(RetunedFrontend::StartupVisible?"Back":"Resume",ImVec2(ImGui::GetFontSize()*6,0)))SetVisibility(false);
#ifdef __APPLE__
            if(RetunedFrontend::TelevisionPlatform())ImGui::TextDisabled("Remote Back / B: categories, then close. View / Minus or L3 + R3: settings.");
            else if(!RetunedFrontend::TouchPlatform())ImGui::TextDisabled("Select / View / Minus or L3 + R3: settings");
#else
            if(!RetunedFrontend::TouchPlatform())ImGui::TextDisabled("Control + comma: settings");
#endif
            ImGui::Separator();
            ImGui::BeginChild("##UnifiedContents",ImVec2(0,-ImGui::GetFontSize()*2.2f));mPanel.Draw();ImGui::EndChild();
            ImGui::Spacing();ImGui::TextDisabled(RetunedFrontend::TelevisionPlatform()?"Directions: move. Right / Click / A: enter page. Left / Back / B: categories. Back / B again: close.":"Settings save automatically. Tap an option or use your controller.");
        }
        ImGui::End();ImGui::GetStyle()=previous;ImGui::GetIO().FontGlobalScale=previousFontScale;ImGui::PopFont();
        RetunedFrontend::SettingsNav.End();
        if(RetunedFrontend::SettingsNav.Close)SetVisibility(false);
        if(!IsVisible())Oot3d::EndGraphicsSettingsPreviews();
    }
