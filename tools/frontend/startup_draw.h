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
#include <algorithm>
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
  const float scale=startupScale,margin=std::min(40.f*scale,w*.05f);
  auto* draw=ImGui::GetWindowDrawList();
  const ImVec2 origin=ImGui::GetWindowPos();
  if(StartupArt) {
   const float size=.375f*std::min(h*.78f,w*.54f);
   const ImVec2 p{origin.x+w*.30f-size*.5f,origin.y+h*.55f-size*.5f};
   draw->AddImage(StartupArt,p,{p.x+size,p.y+size});
  }
  if(InterfaceDisplayFont)ImGui::PushFont(InterfaceDisplayFont);
  constexpr float maximumTitleScale=StartupButtonSize/StartupBodySize;
  const float titleScale=std::min(maximumTitleScale,(w-margin*2)/ImGui::CalcTextSize("Ocarina ReTuned").x);
  ImGui::SetWindowFontScale(titleScale);
  ImGui::SetCursorPos({w-margin-ImGui::CalcTextSize("Ocarina ReTuned").x,30.f*scale});
  ImGui::TextUnformatted("Ocarina ReTuned");
  ImGui::SetWindowFontScale(1.f);
  if(InterfaceDisplayFont)ImGui::PopFont();
  const char* subtitle="Ocarina of Time 3D";
  ImGui::SetCursorPos({w-margin-ImGui::CalcTextSize(subtitle).x,30.f*scale+f*titleScale+8.f*scale});
  ImGui::TextColored(ImGui::GetStyleColorVec4(ImGuiCol_CheckMark),"%s",subtitle);
  if(InterfaceHeadingFont)ImGui::PushFont(InterfaceHeadingFont);
  const auto menu=StartupLayout(w,h,scale,f,MobileSettingsPlatform(),GameFilesReady,ImGui::CalcTextSize("Start game").x);
  ImGui::PushStyleColor(ImGuiCol_Button,ImVec4(0,0,0,0));
  ImGui::PushStyleVar(ImGuiStyleVar_ButtonTextAlign,ImVec2(1.f,.5f));
  ImGui::PushStyleVar(ImGuiStyleVar_FramePadding,ImVec2(12.f*scale,8.f*scale));
  ImGui::SetWindowFontScale(menu.TextScale);
  auto menuButton=[&](const char* label,int row){
   ImGui::SetCursorPos({w-margin-menu.Width,menu.Top+row*(menu.Height+menu.Gap)});
   return ImGui::Button(label,{menu.Width,menu.Height});
  };
  if(menu.ShowSetup) {
   if(menuButton("Setup",0))SetupVisible=true;
  } else if(menuButton("Start game",0)){StartupVisible=false;SetupVisible=false;}
  if(ImGui::IsWindowAppearing())ImGui::SetItemDefaultFocus();
  if(menuButton("Settings",1))Fast::Oot3d::RequestUnifiedSettings();
  if(menuButton("About",2))AboutVisible=true;
  ImGui::SetWindowFontScale(1.f);
  if(InterfaceHeadingFont)ImGui::PopFont();
  ImGui::PopStyleVar(2);ImGui::PopStyleColor();
  ImGui::SetCursorPos({28.f*scale,h-44.f*scale});
  ImGui::SetWindowFontScale(.7f);ImGui::TextDisabled("OCARINA RETUNED  -  v0.5.6 Preview");ImGui::SetWindowFontScale(1.f);
  if(AboutVisible){
   ImGui::SetNextWindowSize({std::min(w*.8f,f*28),0},ImGuiCond_Always);
   if(ImGui::BeginPopupModal("About Ocarina ReTuned",&AboutVisible,ImGuiWindowFlags_AlwaysAutoResize)){
    ImGui::TextUnformatted("Ocarina ReTuned");ImGui::TextDisabled("0.5.6 Preview");ImGui::Spacing();
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
