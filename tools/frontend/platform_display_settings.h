#pragma once
#include <imgui.h>
#include "lower_equipment_state.h"
#if defined(__ANDROID__) && __has_include("android_display_state.h")
#include "android_display_state.h"
#define RETUNED_ANDROID_DISPLAY_SETTINGS 1
#elif defined(__APPLE__) && __has_include("retuned_screen_probe.h")
#include "retuned_screen_probe.h"
#define RETUNED_APPLE_DISPLAY_SETTINGS 1
#endif

namespace RetunedFrontend {
template<class Config, class Toggle>
void DrawPlatformDisplaySettings(const Config& config, Toggle toggle) {
#if defined(RETUNED_ANDROID_DISPLAY_SETTINGS) || defined(RETUNED_APPLE_DISPLAY_SETTINGS)
#ifdef RETUNED_ANDROID_DISPLAY_SETTINGS
    if (!AndroidDualProbeRequested()) return;
    int mode = AndroidDualSelected.load() ? 1 : 0;
#else
    if (!DuoProbeRequested() || !DuoDisplay.Available()) return;
    int mode = DuoDisplay.Preference() == ScreenPreference::Dual ? 1 : 0;
#endif
    ImGui::SeparatorText("Display");
    if (ImGui::Combo("Screen mode", &mode, "Single\0Dual\0")) {
#ifdef RETUNED_ANDROID_DISPLAY_SETTINGS
        AndroidDualSelected = mode == 1;
        AndroidLowerTouch = 0;
#else
        DuoDisplay.Select(mode ? ScreenPreference::Dual : ScreenPreference::Single);
#endif
        config->SetBool("Interface.DualScreen", mode == 1);
        config->Save();
    }
    if (mode == 1) {
        bool panel = LowerEquipmentPanelEnabled.load();
        if (toggle("Bottom equipment panel", &panel)) {
            LowerEquipmentPanelEnabled = panel;
#ifdef RETUNED_ANDROID_DISPLAY_SETTINGS
            AndroidLowerTouch = 0;
#endif
            config->SetBool("Interface.DualEquipmentPanel", panel);
            config->Save();
        }
        ImGui::TextWrapped("Uses spare space below the 4:3 game picture. Best on taller secondary displays, like the AYN Thor.");
    }
#ifdef RETUNED_ANDROID_DISPLAY_SETTINGS
    if (mode == 1 && !AndroidLowerAvailable.load())
        ImGui::TextWrapped("Dual screen uses a connected second display. Using Single until it is available.");
    if (AndroidDualSelected.load() != AndroidGuestDualActive.load())
        ImGui::TextWrapped("Screen mode changes after closing game menus and returning to gameplay.");
#endif
#endif
}
}
