    ImGui::TextDisabled("Select a binding, then press the button or key to use.");
    DrawBindings();
    ImGui::Spacing();
    if (ImGui::CollapsingHeader("Camera and aiming")) {
      DrawFreeCamera();DrawNativeAim();
      if(mTopScreen)DrawTopScreenStickAiming(mTopDraft);
    }
    if (ImGui::CollapsingHeader("Devices and calibration")) {
      DrawDevices();DrawControllerSelection();DrawAnalog();DrawCalibration();
    }
    if (mTopScreen && ImGui::CollapsingHeader("Menu shortcuts"))DrawTopScreenActionBindings(mTopDraft);
    if (mTopScreen && ImGui::CollapsingHeader("Additional gameplay controls"))DrawTopScreenGameplay(mTopDraft);
    if (ImGui::CollapsingHeader("Control presets"))DrawProfile();
