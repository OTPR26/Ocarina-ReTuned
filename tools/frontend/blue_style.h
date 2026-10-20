// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <imgui.h>
namespace RetunedFrontend {
inline void BlueStyle(ImGuiStyle& style) {
    style.WindowPadding={20,18};style.FramePadding={10,7};style.ItemSpacing={10,12};
    style.ItemInnerSpacing={8,6};style.ScrollbarSize=16;style.GrabMinSize=18;
    style.WindowRounding=0;style.ChildRounding=7;style.FrameRounding=4;
    style.PopupRounding=5;style.ScrollbarRounding=8;style.GrabRounding=8;
    style.WindowBorderSize=0;style.ChildBorderSize=0;style.FrameBorderSize=1;
    auto& c=style.Colors;
    c[ImGuiCol_Text]={.94f,.96f,1,1};c[ImGuiCol_TextDisabled]={.58f,.64f,.73f,1};
    c[ImGuiCol_WindowBg]={.025f,.035f,.06f,1};c[ImGuiCol_ChildBg]={.045f,.065f,.10f,1};
    c[ImGuiCol_PopupBg]={.065f,.09f,.15f,1};c[ImGuiCol_Border]={.17f,.25f,.36f,.7f};
    c[ImGuiCol_FrameBg]={.085f,.13f,.21f,1};c[ImGuiCol_FrameBgHovered]={.10f,.23f,.38f,1};
    c[ImGuiCol_FrameBgActive]={.11f,.30f,.52f,1};c[ImGuiCol_Button]={.09f,.17f,.28f,1};
    c[ImGuiCol_ButtonHovered]={.12f,.29f,.48f,1};c[ImGuiCol_ButtonActive]={.14f,.36f,.61f,1};
    c[ImGuiCol_Header]={.08f,.26f,.47f,1};c[ImGuiCol_HeaderHovered]={.10f,.33f,.58f,1};
    c[ImGuiCol_HeaderActive]={.12f,.38f,.67f,1};
    c[ImGuiCol_CheckMark]=c[ImGuiCol_SliderGrab]=c[ImGuiCol_NavCursor]={.39f,.70f,1,1};
    c[ImGuiCol_SliderGrabActive]={.68f,.84f,1,1};c[ImGuiCol_Separator]={.16f,.23f,.33f,1};
    c[ImGuiCol_ScrollbarBg]={0,0,0,0};c[ImGuiCol_ScrollbarGrab]={.21f,.34f,.49f,1};
    c[ImGuiCol_ScrollbarGrabHovered]={.29f,.47f,.65f,1};c[ImGuiCol_ScrollbarGrabActive]={.36f,.60f,.85f,1};
}
}
