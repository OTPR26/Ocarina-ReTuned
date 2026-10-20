// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <map>
namespace RetunedFrontend {
enum class TouchAction { A,B,X,Y,Target,Shield,ItemI,ItemII,Inventory,Settings,Up,Down,Left,Right,Move,Look,Count };
inline int ExtraShoulderAction(bool enabled,int action) {
 if(!enabled)return -1;
 switch(static_cast<TouchAction>(action)) {
 case TouchAction::A:case TouchAction::B:case TouchAction::X:case TouchAction::Y:
 case TouchAction::Target:case TouchAction::Shield:case TouchAction::Inventory:
 case TouchAction::Up:case TouchAction::Down:case TouchAction::Left:case TouchAction::Right:return action;
 default:return -1;
 }
}
struct TouchControl { TouchAction Action; const char* Label; float X,Y,Radius; };
inline constexpr std::array<TouchControl,16> TouchLayout{{
 {TouchAction::A,"A",.91f,.70f,.056f},{TouchAction::B,"B",.82f,.81f,.056f},
 {TouchAction::X,"X",.82f,.58f,.052f},{TouchAction::Y,"Y",.91f,.47f,.052f},
 {TouchAction::Target,"ZL",.25f,.12f,.047f},{TouchAction::Shield,"ZR",.75f,.12f,.047f},
 {TouchAction::ItemI,"L",.12f,.12f,.047f},{TouchAction::ItemII,"R",.88f,.12f,.047f},
 {TouchAction::Inventory,"Start",.44f,.90f,.044f},{TouchAction::Settings,"Settings",.56f,.90f,.044f},
 {TouchAction::Up,"^",.14f,.28f,.038f},{TouchAction::Down,"v",.14f,.44f,.038f},
 {TouchAction::Left,"<",.095f,.36f,.038f},{TouchAction::Right,">",.185f,.36f,.038f},
 {TouchAction::Move,"",.16f,.72f,.12f},{TouchAction::Look,"",.65f,.72f,.095f}
}};
struct TouchSnapshot { uint32_t Buttons=0; float MoveX=0,MoveY=0,LookX=0,LookY=0; bool Captured=false; };
class NativeTouchState {
 uint32_t held=0,pending=0;
 std::map<int,TouchAction> sources;
public:
 float MoveX=0,MoveY=0,LookX=0,LookY=0;
 void Button(TouchAction action,bool down) {
  const auto bit=uint32_t{1}<<static_cast<unsigned>(action);
  if(down){if(!(held&bit))pending|=bit;held|=bit;}else held&=~bit;
 }
 void SourceButton(int source,TouchAction action,bool down) {
  auto previous=sources.find(source);
  if(previous!=sources.end() && (!down || previous->second!=action)) {
   const auto old=previous->second;sources.erase(previous);
   bool another=false;for(const auto& entry:sources)another|=entry.second==old;
   if(!another)Button(old,false);
  }
  if(down && !sources.contains(source)){sources[source]=action;Button(action,true);}
 }
 void Reset(){sources.clear();held=pending=0;MoveX=MoveY=LookX=LookY=0;}
 TouchSnapshot Sample(bool consume){
  TouchSnapshot s{held|pending,MoveX,MoveY,LookX,LookY,held!=0||MoveX!=0||MoveY!=0||LookX!=0||LookY!=0};
  if(consume)pending=0;
  return s;
 }
};
class TouchModel {
 struct Finger { TouchAction Action; float X,Y; };
 std::map<int64_t,Finger> fingers;
 uint32_t pending=0;
 float aspect=16.f/9.f;
public:
 void SetAspect(float value) { aspect=std::max(value,.5f); }
 void Reset() { fingers.clear();pending=0; }
 static uint32_t Bit(TouchAction action) { return uint32_t{1}<<static_cast<unsigned>(action); }
 void Down(int64_t id,float x,float y,bool buttons=true) {
  for(const auto& c:TouchLayout) {
   if(!buttons && c.Action!=TouchAction::Settings)continue;
   const float dx=(x-c.X)*aspect,dy=y-c.Y;
   if(dx*dx+dy*dy<=c.Radius*c.Radius) {
    // A second finger cannot steal an already owned stick.
    if(c.Action==TouchAction::Move||c.Action==TouchAction::Look)
     for(const auto& [other,f]:fingers)if(f.Action==c.Action)return;
    fingers[id]={c.Action,x,y};
    if(c.Action!=TouchAction::Move&&c.Action!=TouchAction::Look)pending|=Bit(c.Action);
    return;
   }
  }
 }
 void Motion(int64_t id,float x,float y) { if(auto i=fingers.find(id);i!=fingers.end()){i->second.X=x;i->second.Y=y;} }
 void Up(int64_t id) { fingers.erase(id); }
 TouchSnapshot Sample(bool consume) {
  TouchSnapshot s;s.Buttons=pending;s.Captured=!fingers.empty();
  for(const auto& [id,f]:fingers) {
   if(f.Action!=TouchAction::Move&&f.Action!=TouchAction::Look){s.Buttons|=Bit(f.Action);continue;}
   const auto& c=TouchLayout[f.Action==TouchAction::Move?14:15];
   float x=(f.X-c.X)*aspect/c.Radius,y=(c.Y-f.Y)/c.Radius;
   const float length=std::hypot(x,y);if(length>1){x/=length;y/=length;}
   if(length<.12f)x=y=0;
   if(f.Action==TouchAction::Move){s.MoveX=x;s.MoveY=y;}else{s.LookX=x;s.LookY=y;}
  }
  if(consume)pending=0;
  return s;
 }
};
}
