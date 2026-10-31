// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "retuned_game_save.h"
#include <imgui.h>
namespace RetunedFrontend {
inline void DrawDualGameSave(bool dual, bool playing) {
    if (!dual || !playing) return;
    ImGui::BeginDisabled(!GameSave.Available());
    if (ImGui::Button("Save game")) GameSave.Request();
    ImGui::EndDisabled();
    if (!GameSave.Available())
        ImGui::TextWrapped("Return to gameplay to open the save dialogue.");
    ImGui::Spacing();
}
}
