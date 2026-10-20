// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "fast/oot3d/retuned_touch_hud_state.h"
#include "oot3d_native_a32_memory.h"
#include "oot3d_ui/ui_primitives.h"
#include "oot3d_ui/ui_contract_types.h"
#include <nlohmann/json.hpp>
#include <fstream>
#include <filesystem>
#include <vector>
namespace RetunedFrontend {
struct TouchHudBridge {
 uint32_t Upload=0,PrepareAction=0,Positions=0,PauseLayout=0,OcarinaLayout=0,ActionSource=0,UVs=0,ActionOwner=0;
 std::array<float,33*12> ItemPositions{};
 bool HaveItems=false,HaveAction=false;
 std::array<float,24> ActionPositions{};
 std::array<float,16> ActionUVs{};
 std::array<float,32> ActionColors{};
 bool Ready()const{return Upload&&PrepareAction&&Positions&&PauseLayout&&OcarinaLayout&&ActionSource&&UVs;}
 bool Gameplay(Oot3dNativeGame::NativeA32Memory& memory)const {
  uint8_t pause=1,instrument=1;
  return Ready()&&TouchHudActive.load()&&memory.Read8(PauseLayout,&pause)&&memory.Read8(OcarinaLayout,&instrument)&&!pause&&!instrument;
 }
 void PlaceItems(Oot3dNativeGame::NativeA32Memory& memory) {
  if(!Gameplay(memory))return;
  std::array<float,33*12> positions{};
  if(!memory.ReadBytes(Positions,std::span(reinterpret_cast<uint8_t*>(positions.data()),sizeof(positions))))return;
  if(!PlaceTouchHud(positions,SnapshotTouchHud(),TouchHudAspect.load()))return;
  ItemPositions=positions;HaveItems=true;
  for(unsigned q:{5u,6u,7u,8u,9u,10u,11u,12u,23u,28u,29u})for(unsigned v=0;v<4;++v){positions[q*12+v*3]=0;positions[q*12+v*3+1]=0;}
  memory.WriteBytes(Positions,std::span(reinterpret_cast<const uint8_t*>(positions.data()),sizeof(positions)));
 }
 std::vector<oot3d::ui::UiPrimitive> Overlay(Oot3dNativeGame::NativeA32Memory& memory,const oot3d::ui::UiTextureIdentity& atlas,const oot3d::ui::UiTextureIdentity* actionAtlas=nullptr)const {
  std::vector<oot3d::ui::UiPrimitive> result;
  if(!HaveItems||!TouchHudLive.load()||!Gameplay(memory))return result;
  std::array<float,33*8> uv{};
  if(!memory.ReadBytes(UVs,std::span(reinterpret_cast<uint8_t*>(uv.data()),sizeof(uv))))return result;
  const float aspect=TouchHudAspect.load();
  for(unsigned q:{5u,6u,7u,8u,9u,10u,11u,12u,23u,28u,29u}) {
   oot3d::ui::UiPrimitive p;p.subsystem=oot3d::ui::UiSubsystem::GameplayHud;
   p.role=q==12||q>=23?oot3d::ui::UiPrimitiveRole::AmmoCounter:oot3d::ui::UiPrimitiveRole::AssignedItem;
   p.texture=atlas;p.layer=q==12||q>=23?21:20;p.source_quad=q;p.color.alpha=TouchIconOpacity.load();
   std::array<oot3d::ui::UiVertex,4> corners{};
   // Native lower-left/right, upper-left/right becomes the host's top-first strip.
   for(unsigned i=0;i<4;++i){const unsigned v=(i+2)%4;
    const auto point=TouchHudWindowPoint(ItemPositions[q*12+v*3],ItemPositions[q*12+v*3+1],aspect);
    corners[i]={point[0],point[1],uv[q*8+v*2],1-uv[q*8+v*2+1]};}
   p.corners=corners;p.destination={corners[0].x,corners[0].y,corners[1].x-corners[0].x,corners[2].y-corners[0].y};
   result.push_back(std::move(p));
  }
  if(HaveAction&&actionAtlas)for(unsigned q=0;q<2;++q){
   float minX=ActionPositions[q*12],maxX=minX,minY=ActionPositions[q*12+1],maxY=minY;
   for(unsigned v=1;v<4;++v){minX=std::min(minX,ActionPositions[q*12+v*3]);maxX=std::max(maxX,ActionPositions[q*12+v*3]);minY=std::min(minY,ActionPositions[q*12+v*3+1]);maxY=std::max(maxY,ActionPositions[q*12+v*3+1]);}
   if(maxY-minY<1||maxX-minX<1)continue;
   oot3d::ui::UiPrimitive p;p.subsystem=oot3d::ui::UiSubsystem::GameplayHud;p.role=oot3d::ui::UiPrimitiveRole::ActionButton;
   p.texture=*actionAtlas;p.layer=22;p.source_quad=q;
   p.color={ActionColors[q*16],ActionColors[q*16+1],ActionColors[q*16+2],ActionColors[q*16+3]*TouchIconOpacity.load()};
   std::array<oot3d::ui::UiVertex,4> corners{};
   for(unsigned i=0;i<4;++i){const unsigned v=(i+2)%4;const auto point=TouchHudWindowPoint(ActionPositions[q*12+v*3],ActionPositions[q*12+v*3+1],aspect);corners[i]={point[0],point[1],ActionUVs[q*8+v*2],1-ActionUVs[q*8+v*2+1]};}
   p.corners=corners;p.destination={corners[0].x,corners[0].y,corners[1].x-corners[0].x,corners[2].y-corners[0].y};result.push_back(std::move(p));
  }
  return result;
 }
 void PlaceAction(Oot3dNativeGame::NativeA32Memory& memory) {
  HaveAction=false;
  if(!Gameplay(memory))return;
  uint32_t source=0;if(!memory.Read32(ActionSource,&source)||!source)return;
  std::array<float,24> positions{};
  if(!memory.ReadBytes(source,std::span(reinterpret_cast<uint8_t*>(positions.data()),sizeof(positions))))return;
  if(!PlaceTouchAction(positions,SnapshotTouchHud()[0],TouchHudAspect.load()))return;
  uint32_t board=0,uv=0,colors=0;
  if(ActionOwner&&memory.Read32(ActionOwner,&board)&&board&&memory.Read32(board+0x14,&uv)&&uv&&memory.Read32(board+0x18,&colors)&&colors&&
     memory.ReadBytes(uv,std::span(reinterpret_cast<uint8_t*>(ActionUVs.data()),sizeof(ActionUVs)))&&
     memory.ReadBytes(colors,std::span(reinterpret_cast<uint8_t*>(ActionColors.data()),sizeof(ActionColors)))){
    ActionPositions=positions;HaveAction=true;
    for(unsigned q=0;q<2;++q)for(unsigned v=0;v<4;++v){positions[q*12+v*3]=0;positions[q*12+v*3+1]=0;}
  }
  memory.WriteBytes(source,std::span(reinterpret_cast<const uint8_t*>(positions.data()),sizeof(positions)));
 }
};
inline TouchHudBridge NativeTouchHud;
inline std::vector<uint32_t> InitializeTouchHudBridge(const std::filesystem::path& manifest) {
 NativeTouchHud={};
#if defined(__IOS__) || defined(__ANDROID__)
 std::ifstream input(manifest);nlohmann::json root;input>>root;
 if(!root.contains("reframed_frontend")||!root["reframed_frontend"].contains("touch_hud"))return {};
 const auto& b=root["reframed_frontend"]["touch_hud"];
 NativeTouchHud={b.at("upload_positions"),b.at("prepare_action"),b.at("positions"),b.at("pause_layout"),b.at("ocarina_layout"),b.at("action_source"),b.value("uvs",0u),b.value("action_owner",0u)};
 if(NativeTouchHud.Ready())return {NativeTouchHud.Upload,NativeTouchHud.PrepareAction};
#endif
 return {};
}
}
