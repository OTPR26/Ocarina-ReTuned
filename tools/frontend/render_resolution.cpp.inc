    const auto metrics = GraphicsSettingsRuntime::Instance().DisplayMetrics();
    const auto& io = ImGui::GetIO();
    const uint32_t outputWidth = metrics.OutputWidth ? metrics.OutputWidth :
        std::max(1U, uint32_t(std::lround(io.DisplaySize.x * io.DisplayFramebufferScale.x)));
    const uint32_t outputHeight = metrics.OutputHeight ? metrics.OutputHeight :
        std::max(1U, uint32_t(std::lround(io.DisplaySize.y * io.DisplayFramebufferScale.y)));
    const bool upscalerOwnsScale = settings.AntiAliasing == AntiAliasingMode::Upscaler;
    const float scale = ResolveInternalResolutionScale(settings);
    const auto extent = RetunedFrontend::GameplayResolution(outputWidth, outputHeight, scale);
    const std::string preview = std::to_string(extent.Width) + " x " + std::to_string(extent.Height);
    ImGui::BeginDisabled(upscalerOwnsScale);
    if (ImGui::BeginCombo("Gameplay resolution", preview.c_str())) {
        for (uint32_t height : {720U, 1080U, 1440U, 2160U}) {
            const float candidate = float(height) / outputHeight;
            if (candidate < RetunedFrontend::MinimumRenderScale - .0001f || candidate > 2.f) continue;
            const auto resolution = RetunedFrontend::GameplayResolution(outputWidth, outputHeight, candidate);
            const std::string label = std::to_string(resolution.Width) + " x " +
                std::to_string(resolution.Height) + " (" + std::to_string(height) + "p)";
            const bool selected = extent.Height == height;
            if (ImGui::Selectable(label.c_str(), selected)) {
                settings.InternalResolutionScale = candidate;
                mRenderScaleEditing = false;
                changed = true;
            }
            if (selected) ImGui::SetItemDefaultFocus();
        }
        const bool selected = std::abs(settings.InternalResolutionScale - 1.f) < .0001f;
        if (ImGui::Selectable("Match display resolution", selected)) {
            settings.InternalResolutionScale = 1.f;
            mRenderScaleEditing = false;
            changed = true;
        }
        ImGui::EndCombo();
    }
    if (!mRenderScaleEditing) mPendingRenderScale = settings.InternalResolutionScale;
    float percent = mPendingRenderScale * 100.f;
    if (ImGui::SliderFloat("Render scale (% of display)", &percent,
                           RetunedFrontend::MinimumRenderScale * 100.f, 200.f, "%.1f%%")) {
        mPendingRenderScale = RetunedFrontend::GameplayScale(percent / 100.f);
        mRenderScaleEditing = true;
    }
    if (mRenderScaleEditing && ImGui::IsItemDeactivatedAfterEdit()) {
        settings.InternalResolutionScale = mPendingRenderScale;
        mRenderScaleEditing = false;
        changed = true;
    }
    ImGui::EndDisabled();
    ImGui::TextWrapped("Gameplay renders internally at the resolution above, then scales to the display. "
                       "100%% matches the display; it does not mean native 3DS resolution.");
    ImGui::Text("Display: %u x %u", outputWidth, outputHeight);
    if (upscalerOwnsScale) ImGui::TextDisabled("Gameplay resolution is set by upscaler quality.");
