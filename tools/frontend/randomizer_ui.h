// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "retuned_frontend_state.h"
#include "fast/oot3d/graphics_settings_window.h"
#include <algorithm>
#include <imgui.h>
#include "ship/Context.h"
#include "ship/config/Config.h"

namespace RetunedFrontend {
inline void LoadRandomizerPreferences() {
    static bool loaded = false;
    if (loaded) return;
    auto config = Ship::Context::GetRawInstance()->GetConfig();
    const auto seed = config->GetString("Randomizer.DraftSeed", "");
    std::copy_n(seed.data(), std::min(seed.size(), RandomizerMenu.SeedInput.size()-1), RandomizerMenu.SeedInput.data());
    RandomizerMenu.SelectedAtStartup = config->GetBool("Randomizer.SelectedAtStartup", false);
    loaded = true;
}
inline void SaveRandomizerPreferences() {
    auto config = Ship::Context::GetRawInstance()->GetConfig();
    config->SetString("Randomizer.DraftSeed", RandomizerMenu.SeedInput.data());
    config->SetBool("Randomizer.SelectedAtStartup", RandomizerMenu.SelectedAtStartup);
    config->Save();
}
inline void DrawRandomizerRules() {
    ImGui::TextUnformatted("Original adventure");
    ImGui::TextWrapped("Glitchless logic. Start as child Link. Original dungeons and entrances. Songs and shops stay unchanged. Keys stay in their own dungeons.");
}
inline void DrawRandomizerSettings() {
    LoadRandomizerPreferences();
    auto& menu = RandomizerMenu;
    if (!menu.Available()) {
        ImGui::TextWrapped("Randomizer is not available in this prepared game.");
        return;
    }
    ImGui::SeparatorText("Next randomizer game");
    ImGui::TextWrapped("These settings apply only when creating an empty randomizer slot.");
    ImGui::BeginDisabled(menu.Busy || menu.TransferBusy);
    ImGui::InputText("Seed", menu.SeedInput.data(), menu.SeedInput.size());
    if (ImGui::IsItemDeactivatedAfterEdit()) SaveRandomizerPreferences();
    ImGui::EndDisabled();
    ImGui::TextDisabled("Leave blank for a new seed.");
    ImGui::SeparatorText("Rules");
    DrawRandomizerRules();
    if (menu.ActiveSlot >= 0) {
        ImGui::SeparatorText("Current game");
        ImGui::Text("Randomizer slot %d", menu.ActiveSlot + 1);
        ImGui::TextWrapped("Seed: %s", menu.ActiveSeed.c_str());
        ImGui::TextDisabled("This run keeps the rules it was created with.");
    }
    if (!menu.Status.empty()) ImGui::TextWrapped("%s", menu.Status.c_str());
    if (!menu.TransferStatus.empty()) ImGui::TextWrapped("%s", menu.TransferStatus.c_str());
}
inline void DrawRandomizerSlots(float inset) {
    auto& menu = RandomizerMenu;
    if (!menu.SlotsVisible || !menu.Available()) return;
    if (ImGui::BeginChild("Randomizer games", {-inset, -ImGui::GetFontSize()*2-inset}, ImGuiChildFlags_NavFlattened)) {
        ImGui::SeparatorText("Randomizer");
        for (unsigned i = 0; i < menu.Slots.size(); ++i) {
            const auto& slot = menu.Slots[i];
            ImGui::PushID(static_cast<int>(i));
            ImGui::Separator();
            ImGui::Text("Slot %u", i + 1);
            if (slot.Status == RandomizerSlotStatus::Empty) {
                ImGui::BeginDisabled(!menu.CanCreate(i, StartupVisible));
                if(menu.FocusSlots) {ImGui::SetKeyboardFocusHere();menu.FocusSlots=false;}
                if (ImGui::Button("New randomized game")) menu.Create(i, menu.SeedInput.data());
                if(menu.ChooseImport) {
                    ImGui::SameLine();
                    if(ImGui::Button("Import run"))menu.ChooseImport(i);
                }
                ImGui::EndDisabled();
            } else if (slot.Status == RandomizerSlotStatus::Ready) {
                ImGui::TextWrapped("Seed: %s", slot.Seed.c_str());
                ImGui::BeginDisabled(!menu.CanStart(i, StartupVisible));
                if(menu.FocusSlots) {ImGui::SetKeyboardFocusHere();menu.FocusSlots=false;}
                if (ImGui::Button("Continue")) menu.Start(i);
                if(menu.ChooseExport) {
                    ImGui::SameLine();
                    if(ImGui::Button("Export run"))menu.ChooseExport(i);
                }
                ImGui::EndDisabled();
            } else ImGui::TextWrapped("%s", slot.Message.c_str());
            ImGui::PopID();
        }
        if (!menu.Status.empty()) ImGui::TextWrapped("%s", menu.Status.c_str());
    if (!menu.TransferStatus.empty()) ImGui::TextWrapped("%s", menu.TransferStatus.c_str());
        ImGui::Separator();
        ImGui::BeginDisabled(menu.Busy || menu.TransferBusy);
        if (ImGui::Button("Randomizer settings")) {
            RequestedSettingsPage = static_cast<int>(SettingsPage::Randomizer);
            menu.SlotsVisible = false;
            Fast::Oot3d::RequestUnifiedSettings();

        }
        ImGui::SameLine();
        if (ImGui::Button("Back") || ImGui::IsKeyPressed(ImGuiKey_Escape, false) ||
            ImGui::IsKeyPressed(ImGuiKey_GamepadFaceRight, false)) menu.SlotsVisible = false;
        ImGui::EndDisabled();
    }
    ImGui::EndChild();
    if(menu.DrawTransfer)menu.DrawTransfer();
}
}
