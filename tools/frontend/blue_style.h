// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <imgui.h>
#include <algorithm>
namespace RetunedFrontend {
inline void BlueStyle(ImGuiStyle& style) {
    style.WindowPadding={18,16};style.FramePadding={12,8};style.ItemSpacing={10,10};
    style.ItemInnerSpacing={8,6};style.ScrollbarSize=16;style.GrabMinSize=18;
    style.WindowRounding=0;style.ChildRounding=10;style.FrameRounding=7;
    style.PopupRounding=5;style.ScrollbarRounding=8;style.GrabRounding=8;
    style.WindowBorderSize=0;style.ChildBorderSize=0;style.FrameBorderSize=0;
    auto& c=style.Colors;
    c[ImGuiCol_Text]={.949f,.949f,.949f,1};c[ImGuiCol_TextDisabled]={.60f,.63f,.69f,1};
    c[ImGuiCol_WindowBg]={.031f,.027f,.051f,1};c[ImGuiCol_ChildBg]={.051f,.063f,.090f,1};
    c[ImGuiCol_PopupBg]={.067f,.082f,.122f,1};c[ImGuiCol_Border]={.20f,.25f,.34f,.7f};
    c[ImGuiCol_FrameBg]={.110f,.145f,.220f,1};c[ImGuiCol_FrameBgHovered]={.12f,.20f,.32f,1};
    c[ImGuiCol_FrameBgActive]={.08f,.24f,.41f,1};c[ImGuiCol_Button]={.110f,.145f,.220f,1};
    c[ImGuiCol_ButtonHovered]={.08f,.24f,.41f,1};c[ImGuiCol_ButtonActive]={.10f,.29f,.49f,1};
    c[ImGuiCol_Header]={.078f,.239f,.408f,1};c[ImGuiCol_HeaderHovered]={.10f,.29f,.49f,1};
    c[ImGuiCol_HeaderActive]={.12f,.33f,.55f,1};
    c[ImGuiCol_CheckMark]=c[ImGuiCol_SliderGrab]=c[ImGuiCol_NavCursor]={.49f,.67f,.95f,1};
    c[ImGuiCol_SliderGrabActive]={.70f,.82f,1,1};c[ImGuiCol_Separator]={.16f,.20f,.28f,1};
    c[ImGuiCol_ScrollbarBg]={0,0,0,0};c[ImGuiCol_ScrollbarGrab]={.28f,.35f,.47f,1};
    c[ImGuiCol_ScrollbarGrabHovered]={.34f,.44f,.59f,1};c[ImGuiCol_ScrollbarGrabActive]={.40f,.54f,.72f,1};
}
}
namespace RetunedFrontend {
inline bool Toggle(const char* label,bool* value) {
    const float f=ImGui::GetFontSize(),width=std::min(ImGui::GetContentRegionAvail().x,f*32),height=f*2.4f;
    const auto p=ImGui::GetCursorScreenPos();
    const bool pressed=ImGui::InvisibleButton(label,{width,height},ImGuiButtonFlags_EnableNav);if(pressed)*value=!*value;
    auto* draw=ImGui::GetWindowDrawList();
    draw->AddRectFilled(p,{p.x+width,p.y+height},ImGui::GetColorU32(ImGui::IsItemHovered()?ImGuiCol_FrameBgHovered:ImGuiCol_FrameBg),7);
    draw->AddText({p.x+f*.65f,p.y+(height-f)*.5f},ImGui::GetColorU32(ImGuiCol_Text),label);
    const ImVec2 a{p.x+width-f*3.1f,p.y+(height-f)*.5f};
    draw->AddRectFilled(a,{a.x+f*2.2f,a.y+f},ImGui::GetColorU32(*value?ImGuiCol_CheckMark:ImGuiCol_Border),f*.5f);
    draw->AddCircleFilled({a.x+f*(*value?1.7f:.5f),a.y+f*.5f},f*.34f,ImGui::GetColorU32(ImGuiCol_Text));
    if(ImGui::IsItemFocused())draw->AddRect(p,{p.x+width,p.y+height},ImGui::GetColorU32(ImGuiCol_CheckMark),7,0,2);
    return pressed;
}
}
