// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "retuned_desktop_folder_model.h"
#include <imgui.h>
#include <cstdio>

namespace RetunedFrontend {
inline bool DrawDesktopTexturePicker(std::string& selected) {
    using namespace DesktopFolders;
    static Browser browser;
    static char location[32768]{};
    const auto open = [&](const fs::path& path) {
        browser.Open(path);
        std::snprintf(location, sizeof(location), "%s", Text(browser.directory).c_str());
    };
    if (ImGui::Button("Choose texture folder")) {
        browser.Begin(selected);
        open(browser.directory);
        ImGui::OpenPopup("Texture folder");
    }
    bool changed = false;
    const auto available = ImGui::GetIO().DisplaySize;
    ImGui::SetNextWindowSize({std::min(720.f, available.x * .9f),
                              std::min(520.f, available.y * .9f)}, ImGuiCond_Appearing);
    if (ImGui::BeginPopupModal("Texture folder", nullptr, ImGuiWindowFlags_NoSavedSettings)) {
        ImGui::TextWrapped("Choose your extracted texture pack. Subfolders are included.");
        ImGui::SetNextItemWidth(-70.f);
        bool go = ImGui::InputText("##location", location, sizeof(location), ImGuiInputTextFlags_EnterReturnsTrue);
        ImGui::SameLine();
        go = ImGui::Button("Go") || go;
        if (go) open(Path(location));
        if (ImGui::Button("Home")) open(Home());
        ImGui::SameLine();
        if (ImGui::Button("Parent folder")) open(browser.directory.parent_path());
        ImGui::SameLine();
        if (ImGui::BeginCombo("##drives", "Drives")) {
            for (const auto& root : Roots())
                if (ImGui::Selectable(Text(root).c_str())) open(root);
            ImGui::EndCombo();
        }
        if (!browser.listing.error.empty()) ImGui::TextWrapped("%s", browser.listing.error.c_str());
        if (browser.listing.truncated) ImGui::TextWrapped("Large folder: enter a path or choose a subfolder.");
        ImGui::BeginChild("Folders", {0, -ImGui::GetFrameHeightWithSpacing() * 2.f}, true);
        fs::path enter;
        for (const auto& folder : browser.listing.directories) {
            ImGui::PushID(Text(folder).c_str());
            if (ImGui::Selectable(Text(folder.filename()).c_str())) enter = folder;
            ImGui::PopID();
        }
        ImGui::EndChild();
        if (!enter.empty()) open(enter);
        ImGui::BeginDisabled(!browser.CanSelect());
        if (ImGui::Button("Select this folder")) {
            selected = Text(browser.directory);
            changed = true;
            ImGui::CloseCurrentPopup();
        }
        ImGui::EndDisabled();
        ImGui::SameLine();
        if (ImGui::Button("Cancel")) ImGui::CloseCurrentPopup();
        ImGui::EndPopup();
    }
    return changed;
}
}
