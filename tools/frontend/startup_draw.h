// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "retuned_frontend_state.h"
#include "retuned_responsive_layout.h"
#include "retuned_artwork.h"
#include "retuned_startup_layout.h"
#include "retuned_menu_navigation.h"
#include "fast/Fast3dGui.h"
#include "fast/oot3d/graphics_settings_window.h"
#include "ship/Context.h"
#include "retuned_randomizer_ui.h"
#include <algorithm>
#if defined(__APPLE__) && TARGET_OS_IOS && !TARGET_OS_TV
extern "C" bool RetunedIsIPhone();
#endif
namespace RetunedFrontend {
inline ImTextureID StartupArt=0;
inline bool AboutVisible=false;
inline void LoadStartupArt(Fast::Fast3dGui& gui) {
 if(gui.HasTextureByName("retuned-ocarina")) {
  StartupArt=gui.GetTextureByName("retuned-ocarina");
  return;
 }
 auto texture=std::make_shared<Ship::GuiTexture>();
 texture->Data=stbi_load_from_memory(OcarinaArtwork,sizeof(OcarinaArtwork),&texture->Metadata.Width,&texture->Metadata.Height,nullptr,4);
 if(!texture->Data)return;
 texture->DataSize=texture->Metadata.Width*texture->Metadata.Height*4;
 gui.LoadTextureFromResource("retuned-ocarina",texture);
 StartupArt=gui.GetTextureByName("retuned-ocarina");
}
inline void DrawStartup(Fast::Fast3dGui& gui,bool settingsVisible) {
 if(!NativeFrontendEnabled||!StartupVisible||settingsVisible)return;
 LoadStartupArt(gui);
 LoadRandomizerPreferences();
 const auto* viewport=ImGui::GetMainViewport();
 const auto previous=ImGui::GetStyle();const float oldScale=ImGui::GetIO().FontGlobalScale;
 const float startupScale=MobileSettingsPlatform()?MenuScale(viewport->WorkSize.y)/std::max(MenuSize,.1f):MenuScale(viewport->WorkSize.y);
 BlueStyle(ImGui::GetStyle());ImGui::GetIO().FontGlobalScale=InterfaceFontScale(startupScale,StartupBodySize);
 ImGui::GetStyle().ScaleAllSizes(startupScale);
 // Refresh ImGui's cached font metrics after changing the interface scale.
 ImGui::PushFont(ImGui::GetFont());
 ImGui::SetNextWindowPos(viewport->WorkPos);ImGui::SetNextWindowSize(viewport->WorkSize);
 constexpr auto flags=ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoMove|ImGuiWindowFlags_NoDocking|ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoScrollbar|ImGuiWindowFlags_NoScrollWithMouse;
 if(ImGui::Begin("Ocarina ReTuned / Startup",nullptr,flags)) {
  const float f=ImGui::GetFontSize(),w=ImGui::GetWindowWidth(),h=ImGui::GetWindowHeight();
  const float scale=startupScale;
#if defined(__APPLE__) && TARGET_OS_IOS && !TARGET_OS_TV
  const float inset=RetunedIsIPhone()?std::min(12.f*scale,h*.03f):0.f;
#else
  constexpr float inset=0.f;
#endif
  const float margin=std::min(40.f*scale,w*.05f)+inset;
  auto* draw=ImGui::GetWindowDrawList();
  const ImVec2 origin=ImGui::GetWindowPos();
  if(StartupArt && !RandomizerMenu.SlotsVisible) {
   const float size=.375f*std::min(h*.78f,w*.54f);
   const ImVec2 p{origin.x+w*.30f-size*.5f,origin.y+h*.55f-size*.5f};
   draw->AddImage(StartupArt,p,{p.x+size,p.y+size});
  }
#if defined(__SWITCH__)
  constexpr float optionSize=42.f, headingScale=2.3f, subtitleSize=2.1f, versionScale=1.7f;
#elif defined(__APPLE__) && TARGET_OS_IOS && !TARGET_OS_TV
  constexpr float optionSize=38.f, headingScale=1.5f, subtitleSize=1.5f, versionScale=.7f;
#else
  constexpr float optionSize=32.f, headingScale=1.f, subtitleSize=1.f, versionScale=.7f;
#endif
  if(InterfaceDisplayFont)ImGui::PushFont(InterfaceDisplayFont);
  constexpr float maximumTitleScale=headingScale*StartupButtonSize/StartupBodySize;
  const float titleScale=std::min(maximumTitleScale,(w-margin*2)/ImGui::CalcTextSize("Ocarina ReTuned").x);
  ImGui::SetWindowFontScale(titleScale);
  ImGui::SetCursorPos({w-margin-ImGui::CalcTextSize("Ocarina ReTuned").x,inset+30.f*scale});
  ImGui::TextUnformatted("Ocarina ReTuned");
  ImGui::SetWindowFontScale(1.f);
  if(InterfaceDisplayFont)ImGui::PopFont();
  const char* subtitle="Ocarina of Time 3D";
  const float subtitleScale=std::min(subtitleSize,(w-2*margin)/ImGui::CalcTextSize(subtitle).x);
  ImGui::SetWindowFontScale(subtitleScale);
  ImGui::SetCursorPos({w-margin-ImGui::CalcTextSize(subtitle).x,inset+30.f*scale+f*titleScale+8.f*scale});
  ImGui::TextColored(ImGui::GetStyleColorVec4(ImGuiCol_CheckMark),"%s",subtitle);
  ImGui::SetWindowFontScale(1.f);
  if(RandomizerMenu.SlotsVisible && RandomizerMenu.Available()) {
   ImGui::SetCursorPos({margin, inset+f*4+40.f*scale});
   DrawRandomizerSlots(inset);
  } else {
  if(InterfaceHeadingFont)ImGui::PushFont(InterfaceHeadingFont);
  const bool fitModeArrows=optionSize>32.f && GameFilesReady && RandomizerMenu.Available();
  const float labelWidth=fitModeArrows?std::max(ImGui::CalcTextSize("Randomizer").x,ImGui::CalcTextSize("Start game").x):ImGui::CalcTextSize("Start game").x;
  const auto menu=StartupLayout(w,h,scale,f,MobileSettingsPlatform(),GameFilesReady,labelWidth,optionSize,fitModeArrows);
  ImGui::PushStyleColor(ImGuiCol_Button,ImVec4(0,0,0,0));
  ImGui::PushStyleVar(ImGuiStyleVar_ButtonTextAlign,ImVec2(1.f,.5f));
  ImGui::PushStyleVar(ImGuiStyleVar_FramePadding,ImVec2(12.f*scale,8.f*scale));
  ImGui::SetWindowFontScale(menu.TextScale);
  int stickTarget=-1;
  if(!AboutVisible && !SetupVisible) {
   const int vertical=int(ImGui::IsKeyPressed(ImGuiKey_GamepadLStickDown))-
                      int(ImGui::IsKeyPressed(ImGuiKey_GamepadLStickUp));
   if(vertical) {
    const auto focused=ImGui::GetCurrentContext()->NavId;
    const int row=focused==ImGui::GetID("About")?2:focused==ImGui::GetID("Settings")?1:0;
    stickTarget=std::clamp(row+vertical,0,2);
   }
  }
  auto menuButton=[&](const char* label,int row,bool mode=false){
   ImGui::SetCursorPos({w-margin-menu.Width,menu.Top-inset+row*(menu.Height+menu.Gap)});
   ImGui::PushStyleColor(ImGuiCol_NavCursor,ImVec4(0,0,0,0));
   const bool pressed=ImGui::InvisibleButton(label,{menu.Width,menu.Height},ImGuiButtonFlags_EnableNav);
   ImGui::PopStyleColor();
   if(row==stickTarget) {
    ImGui::SetFocusID(ImGui::GetItemID(),ImGui::GetCurrentWindow());
    ImGui::SetNavCursorVisible(true);
   }
   const auto min=ImGui::GetItemRectMin(),max=ImGui::GetItemRectMax();
   const bool selected=ImGui::IsItemHovered() || ImGui::IsItemFocused();
   if(selected || ImGui::IsItemActive()) {
    const ImU32 color=ImGui::GetColorU32(ImGui::IsItemActive()?ImGuiCol_ButtonActive:ImGuiCol_ButtonHovered);
    const int firstVertex=draw->VtxBuffer.Size;
    draw->AddRectFilled(min,max,color,8.f*scale,ImDrawFlags_RoundCornersRight);
    for(int i=firstVertex;i<draw->VtxBuffer.Size;++i) {
     auto& vertex=draw->VtxBuffer[i];
     const float fade=std::clamp((vertex.pos.x-min.x)/(max.x-min.x),0.f,1.f);
     const auto alpha=static_cast<ImU32>((vertex.col>>IM_COL32_A_SHIFT)*fade+.5f);
     vertex.col=(vertex.col & ~IM_COL32_A_MASK)|(alpha<<IM_COL32_A_SHIFT);
    }
   }
   if(!mode) {
    const auto text=ImGui::CalcTextSize(label);
    draw->AddText({max.x-12.f*scale-text.x,min.y+(menu.Height-text.y)*.5f},ImGui::GetColorU32(ImGuiCol_Text),label);
   }
   return pressed;
  };
  if(menu.ShowSetup) {
   if(menuButton("Setup",0))SetupVisible=true;
   if(ImGui::IsWindowAppearing())ImGui::SetItemDefaultFocus();
  } else {
   auto& randomizer=RandomizerMenu;
   const char* label=randomizer.Available()&&randomizer.SelectedAtStartup?"Randomizer":"Start game";
   bool launch=false;
   if(randomizer.Available()) {
    const float arrowWidth=menu.Height*.7f;
    const float modeWidth=std::max(ImGui::CalcTextSize("Randomizer").x,ImGui::CalcTextSize("Start game").x)+2.f*arrowWidth;
    const bool pressed=menuButton("##GameMode",0,true);
    if(ImGui::IsWindowAppearing())ImGui::SetItemDefaultFocus();
    const ImVec2 min=ImGui::GetItemRectMin(),max=ImGui::GetItemRectMax();
    const bool focused=ImGui::IsItemFocused();
    const bool cycleKey=focused&&(ImGui::IsKeyPressed(ImGuiKey_LeftArrow,false)||ImGui::IsKeyPressed(ImGuiKey_RightArrow,false)||
                 ImGui::IsKeyPressed(ImGuiKey_GamepadDpadLeft,false)||ImGui::IsKeyPressed(ImGuiKey_GamepadDpadRight,false)||
                 ImGui::IsKeyPressed(ImGuiKey_GamepadLStickLeft,false)||ImGui::IsKeyPressed(ImGuiKey_GamepadLStickRight,false));
    const float mouseX=ImGui::GetIO().MousePos.x;
    const bool arrowClick=pressed&&ImGui::IsMouseReleased(ImGuiMouseButton_Left)&&
                         ((mouseX>max.x-modeWidth&&mouseX<max.x-modeWidth+arrowWidth)||mouseX>max.x-arrowWidth);
    if(cycleKey||arrowClick) {
     randomizer.SelectedAtStartup=!randomizer.SelectedAtStartup;
     SaveRandomizerPreferences();
    }
    else launch=pressed;
    label=randomizer.SelectedAtStartup?"Randomizer":"Start game";
    const ImVec2 text=ImGui::CalcTextSize(label);
    const auto color=ImGui::GetColorU32(ImGuiCol_Text);
    draw->AddText({max.x-arrowWidth-text.x,min.y+(menu.Height-text.y)*.5f},color,label);
    const float cy=(min.y+max.y)*.5f,tip=ImGui::GetFontSize()*.12f;
    for(int side=0;side<2;++side) {
     const float cx=side?max.x-arrowWidth*.5f:max.x-arrowWidth-text.x-arrowWidth*.5f;
     const float direction=side?1.f:-1.f;
     draw->AddLine({cx-direction*tip,cy-2*tip},{cx+direction*tip,cy},color,2.f*scale);
     draw->AddLine({cx+direction*tip,cy},{cx-direction*tip,cy+2*tip},color,2.f*scale);
    }
   } else {
    launch=menuButton(label,0);
    if(ImGui::IsWindowAppearing())ImGui::SetItemDefaultFocus();
   }
   if(launch) {
    if(randomizer.Available()&&randomizer.SelectedAtStartup) {
     randomizer.Refresh();randomizer.SlotsVisible=true;randomizer.FocusSlots=true;
    } else if(randomizer.ActiveSlot>=0&&randomizer.StartNormal) randomizer.StartNormal();
    else {StartupVisible=false;SetupVisible=false;}
   }
  }
  if(menuButton("Settings",1))Fast::Oot3d::RequestUnifiedSettings();
  if(menuButton("About",2))AboutVisible=true;
  ImGui::SetWindowFontScale(1.f);
  if(InterfaceHeadingFont)ImGui::PopFont();
  ImGui::PopStyleVar(2);ImGui::PopStyleColor();
  }
  ImGui::SetCursorPos({inset+28.f*scale,h-inset-44.f*scale-std::max(0.f,versionScale-.7f)*f});
  ImGui::SetWindowFontScale(versionScale);ImGui::TextDisabled("OCARINA RETUNED  -  v0.8.0 Preview");ImGui::SetWindowFontScale(1.f);
  if(AboutVisible){
   ImGui::SetNextWindowSize({std::min(w*.8f,f*28),0},ImGuiCond_Always);
   if(ImGui::BeginPopupModal("About Ocarina ReTuned",&AboutVisible,ImGuiWindowFlags_AlwaysAutoResize)){
    ImGui::TextUnformatted("Ocarina ReTuned");ImGui::TextDisabled("0.8.0 Preview");ImGui::Spacing();
    ImGui::TextWrapped("Ocarina of Time 3D with the Reframed single-screen HUD.");
    ImGui::Spacing();if(ImGui::Button("Close")||ImGui::IsKeyPressed(ImGuiKey_Escape,false)||ImGui::IsKeyPressed(ImGuiKey_GamepadFaceRight,false)){AboutVisible=false;ImGui::CloseCurrentPopup();}
    ImGui::EndPopup();
   }else ImGui::OpenPopup("About Ocarina ReTuned");
  }
  if(SetupVisible) {
   ImGui::SetNextWindowSize({std::min(w*.84f,f*31),0},ImGuiCond_Always);
   if(ImGui::BeginPopupModal("Game setup",&SetupVisible,ImGuiWindowFlags_AlwaysAutoResize)) {
    ImGui::TextWrapped("This preview uses your prepared native game files. Saves and settings are kept in this app's own storage.");
    ImGui::Spacing();ImGui::TextUnformatted("Game files: ready");
    ImGui::TextWrapped("Choose and manage your texture pack under Settings > Graphics > Custom textures. Controller mappings and game options use the same settings before and during gameplay.");
    if(ImGui::Button("Texture packs")){RequestedSettingsPage=static_cast<int>(SettingsPage::Graphics);Fast::Oot3d::RequestUnifiedSettings();SetupVisible=false;ImGui::CloseCurrentPopup();}
    ImGui::SameLine();if(ImGui::Button("Done")){SetupVisible=false;ImGui::CloseCurrentPopup();}
    ImGui::EndPopup();
   } else ImGui::OpenPopup("Game setup");
  }
 }
 ImGui::End();ImGui::GetStyle()=previous;ImGui::GetIO().FontGlobalScale=oldScale;ImGui::PopFont();
}
}
