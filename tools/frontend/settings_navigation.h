// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <imgui.h>
#include <imgui_internal.h>
namespace RetunedFrontend {
// Settings are two navigation regions. Back first leaves an editor/popup, then
// returns to categories, and only closes Settings from the category region.
struct SettingsNavigation {
    enum class Pane { Categories, Page };
    ImGuiWindow* Categories=nullptr;
    ImGuiWindow* Page=nullptr;
    ImGuiID SelectedCategory=0;
    Pane LastPane=Pane::Categories;
    bool Enabled=false,FocusCategories=false,FocusPage=false,Close=false;
    bool HadPopup=false,HadEditor=false;
    int LastFrame=-2;
    bool Within(ImGuiWindow* window,ImGuiWindow* parent) const {
        return window && parent && (window==parent || ImGui::IsWindowChildOf(window,parent,true,true));
    }
    void Begin(bool television) {
        auto& context=*ImGui::GetCurrentContext();
        Enabled=television || context.NavInputSource==ImGuiInputSource_Gamepad;
        FocusCategories=false;FocusPage=false;Close=false;
        if(!Enabled)return;
        if(LastFrame+1!=context.FrameCount){FocusCategories=true;LastPane=Pane::Categories;HadPopup=false;HadEditor=false;}
        LastFrame=context.FrameCount;
        if(Within(context.NavWindow,Categories))LastPane=Pane::Categories;
        else if(Within(context.NavWindow,Page))LastPane=Pane::Page;
        const bool blocked=HadPopup || HadEditor || ImGui::IsAnyItemActive() ||
            ImGui::IsPopupOpen(nullptr,ImGuiPopupFlags_AnyPopupId|ImGuiPopupFlags_AnyPopupLevel);
        const bool back=ImGui::IsKeyPressed(ImGuiKey_Escape,false)||ImGui::IsKeyPressed(ImGuiKey_GamepadFaceRight,false);
        if(blocked)return; // Dear ImGui cancels the current edit or popup first.
        if(back) {
            if(LastPane==Pane::Page)FocusCategories=true;
            else Close=true;
            ImGui::NavMoveRequestCancel();
        } else if(LastPane==Pane::Page &&
            (ImGui::IsKeyPressed(ImGuiKey_LeftArrow,false)||ImGui::IsKeyPressed(ImGuiKey_GamepadDpadLeft,false))) {
            FocusCategories=true;ImGui::NavMoveRequestCancel();
        } else if(LastPane==Pane::Categories &&
            (ImGui::IsKeyPressed(ImGuiKey_RightArrow,false)||ImGui::IsKeyPressed(ImGuiKey_GamepadDpadRight,false))) {
            FocusPage=true;ImGui::NavMoveRequestCancel();
        }
    }
    void ActivateCategory(ImGuiID id) {
        SelectedCategory=id;
        if(Enabled){FocusPage=true;FocusCategories=false;ImGui::NavMoveRequestCancel();}
    }
    void CategoriesDrawn(float selectedY) {
        Categories=ImGui::GetCurrentWindow();
        if(Enabled && FocusCategories && SelectedCategory) {
            ImGui::NavMoveRequestCancel();
            ImGui::FocusWindow(Categories);ImGui::SetFocusID(SelectedCategory,Categories);
            ImGui::SetNavCursorVisible(true);ImGui::SetScrollFromPosY(selectedY,.5f);
            LastPane=Pane::Categories;FocusCategories=false;
        }
    }
    void PageBegun() {
        Page=ImGui::GetCurrentWindow();
        if(Enabled && FocusPage) {
            ImGui::NavMoveRequestCancel();
            ImGui::FocusWindow(Page);ImGui::NavInitWindow(Page,true);
            ImGui::SetNavCursorVisible(true);LastPane=Pane::Page;FocusPage=false;
        }
    }
    void End() {
        if(!Enabled)return;
        auto* nav=ImGui::GetCurrentContext()->NavWindow;
        if(Within(nav,Categories))LastPane=Pane::Categories;
        else if(Within(nav,Page))LastPane=Pane::Page;
        HadPopup=ImGui::IsPopupOpen(nullptr,ImGuiPopupFlags_AnyPopupId|ImGuiPopupFlags_AnyPopupLevel);
        HadEditor=ImGui::IsAnyItemActive();
    }
};
inline SettingsNavigation SettingsNav;
}
