// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "retuned_frontend_state.h"
#include "retuned_responsive_layout.h"
#include "retuned_artwork.h"
#include "fast/Fast3dGui.h"
#include "fast/oot3d/graphics_settings_window.h"
#include "ship/Context.h"
#include <algorithm>
namespace RetunedFrontend {
inline ImTextureID StartupArt=0;
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
 BlueStyle(ImGui::GetStyle());ImGui::GetIO().FontGlobalScale=.5f*InterfaceScale(viewport->WorkSize.y);
 ImGui::GetStyle().ScaleAllSizes(InterfaceScale(viewport->WorkSize.y));
 ImGui::SetNextWindowPos(viewport->WorkPos);ImGui::SetNextWindowSize(viewport->WorkSize);
 constexpr auto flags=ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoMove|ImGuiWindowFlags_NoDocking|ImGuiWindowFlags_NoSavedSettings;
 if(ImGui::Begin("Ocarina ReTuned / Startup",nullptr,flags)) {
  const float f=ImGui::GetFontSize(),w=ImGui::GetContentRegionAvail().x,h=ImGui::GetContentRegionAvail().y;
  const auto origin=ImGui::GetCursorScreenPos();
  auto* draw=ImGui::GetWindowDrawList();
  draw->AddRectFilledMultiColor(origin,{origin.x+w,origin.y+h},IM_COL32(6,12,25,255),IM_COL32(9,29,53,255),IM_COL32(3,12,27,255),IM_COL32(4,8,18,255));
  if(StartupArt) {
   const float size=std::min(h*.86f,w*.50f);
   const ImVec2 p{origin.x+w*.51f+(w*.49f-size)*.5f,origin.y+(h-size)*.5f};
   draw->AddImage(StartupArt,p,{p.x+size,p.y+size});
  }
  ImGui::SetCursorPos({f*1.4f,h*.16f});
  ImGui::SetWindowFontScale(1.65f);ImGui::TextUnformatted("Ocarina ReTuned");ImGui::SetWindowFontScale(1.f);
  ImGui::SetCursorPosX(f*1.4f);ImGui::TextColored(ImVec4(.45f,.74f,1,1),"Ocarina of Time 3D");
  ImGui::SetCursorPos({f*1.4f,h*.40f});
  const float buttonWidth=std::min(w*.36f,f*18),buttonHeight=std::max(f*2.7f,44.f);
  if(ImGui::Button("Start Game",{buttonWidth,buttonHeight})){StartupVisible=false;SetupVisible=false;}
  if(ImGui::IsWindowAppearing())ImGui::SetItemDefaultFocus();
  ImGui::SetCursorPosX(f*1.4f);
  if(ImGui::Button("Settings",{buttonWidth,buttonHeight}))Fast::Oot3d::RequestUnifiedSettings();
  ImGui::SetCursorPosX(f*1.4f);
  if(ImGui::Button("Setup",{buttonWidth,buttonHeight}))SetupVisible=true;
  ImGui::SetCursorPos({f*1.4f,h-f*2});ImGui::TextDisabled("0.1.0  |  Preview");
  if(SetupVisible) {
   ImGui::SetNextWindowSize({std::min(w*.84f,f*31),0},ImGuiCond_Always);
   if(ImGui::BeginPopupModal("Game setup",&SetupVisible,ImGuiWindowFlags_AlwaysAutoResize)) {
    ImGui::TextWrapped("This preview uses your prepared native game files. Saves and settings are kept in this app's own storage.");
    ImGui::Spacing();ImGui::TextUnformatted("Game files: ready");
    ImGui::TextWrapped("Choose and manage your texture pack under Settings > Textures. Controller mappings and game options use the same settings before and during gameplay.");
    if(ImGui::Button("Texture packs")){RequestedSettingsPage=6;Fast::Oot3d::RequestUnifiedSettings();SetupVisible=false;ImGui::CloseCurrentPopup();}
    ImGui::SameLine();if(ImGui::Button("Done")){SetupVisible=false;ImGui::CloseCurrentPopup();}
    ImGui::EndPopup();
   } else ImGui::OpenPopup("Game setup");
  }
 }
 ImGui::End();ImGui::GetStyle()=previous;ImGui::GetIO().FontGlobalScale=oldScale;
}
}
