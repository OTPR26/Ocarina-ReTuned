// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <array>
#include <algorithm>
#include <utility>
#include <span>
#include <cmath>
namespace RetunedFrontend {
struct TouchHudAnchor {float X=0,Y=0;bool Valid=false;};
using TouchHudAnchors=std::array<TouchHudAnchor,9>; // A B X Y Up Down Left Right ZR
inline std::array<float,2> TouchHudPoint(const TouchHudAnchor& anchor,float aspect) {
 // The game HUD preserves its native aspect inside the full-screen viewport.
 // Invert that centered projection; touch anchors are in full-window space.
 const float width=std::max(400.f,240.f*aspect);
 const float height=std::max(240.f,400.f/aspect);
 return {200.f+(anchor.X-.5f)*width,120.f+(anchor.Y-.5f)*height};
}
inline std::array<float,2> TouchHudWindowPoint(float x,float y,float aspect) {
 const float width=std::max(400.f,240.f*aspect),height=std::max(240.f,400.f/aspect);
 return {(x+(width-400.f)*.5f)/width*400.f,(y+(height-240.f)*.5f)/height*240.f};
}
inline bool ValidTouchHudAnchors(const TouchHudAnchors& anchors) {
 for(unsigned i=0;i<8;++i){const auto& a=anchors[i];if(!a.Valid||!std::isfinite(a.X)||!std::isfinite(a.Y)||a.X<0||a.X>1||a.Y<0||a.Y>1)return false;}
 return true;
}
inline void TranslateHudQuad(std::span<float> positions,unsigned quad,float dx,float dy) {
 for(unsigned v=0;v<4;++v){positions[quad*12+v*3]+=dx;positions[quad*12+v*3+1]+=dy;}
}
inline std::array<float,2> HudQuadCenter(std::span<const float> positions,unsigned quad) {
 float x=0,y=0;for(unsigned v=0;v<4;++v){x+=positions[quad*12+v*3];y+=positions[quad*12+v*3+1];}return {x*.25f,y*.25f};
}
inline bool PlaceTouchHud(std::span<float> positions,const TouchHudAnchors& anchors,float aspect=400.f/240.f,int jumpMode=0) {
 if(jumpMode==2 && (!anchors[8].Valid||!std::isfinite(anchors[8].X)||!std::isfinite(anchors[8].Y)||anchors[8].X<0||anchors[8].X>1||anchors[8].Y<0||anchors[8].Y>1))return false;
 if(positions.size()<33*12 || !ValidTouchHudAnchors(anchors)||!std::isfinite(aspect)||aspect<=0)return false;
 // Quad roles are exported by the Reframed HUD schema, independent of ROM addresses.
 constexpr std::array<unsigned,7> icons{5,6,7,9,11,10,8};
 constexpr std::array<unsigned,7> slots{1,2,3,4,5,6,7};
 std::array<std::array<float,2>,8> delta{};
 for(unsigned i=0;i<icons.size();++i){const auto c=HudQuadCenter(positions,icons[i]);const auto slot=slots[i];const auto target=TouchHudPoint(anchors[jumpMode==2&&slot==2?8:slot],aspect);delta[slot]={target[0]-c[0],target[1]-c[1]};TranslateHudQuad(positions,icons[i],delta[slot][0],delta[slot][1]);}
 for(const auto [quad,slot]:std::array{std::pair{12u,6u},std::pair{23u,5u},std::pair{28u,2u},std::pair{29u,3u}})TranslateHudQuad(positions,quad,delta[slot][0],delta[slot][1]);
 // The native touch controller supplies these button bases and D-pad cross.
 for(unsigned q=1;q<=4;++q)for(unsigned v=0;v<4;++v){positions[q*12+v*3]=0;positions[q*12+v*3+1]=0;}
 return true;
}
inline bool PlaceTouchAction(std::span<float> positions,const TouchHudAnchor& anchor,float aspect=400.f/240.f) {
 if(positions.size()!=24||!anchor.Valid||!std::isfinite(aspect)||aspect<=0)return false;
 const auto target=TouchHudPoint(anchor,aspect);
 for(unsigned q=0;q<2;++q){float minX=positions[q*12],maxX=minX,minY=positions[q*12+1],maxY=minY;
  for(unsigned v=1;v<4;++v){minX=std::min(minX,positions[q*12+v*3]);maxX=std::max(maxX,positions[q*12+v*3]);minY=std::min(minY,positions[q*12+v*3+1]);maxY=std::max(maxY,positions[q*12+v*3+1]);}
  if(maxY-minY>=1 && maxX-minX>(maxY-minY)*1.35f) {
   const auto center=HudQuadCenter(positions,q);
   TranslateHudQuad(positions,q,target[0]-center[0],target[1]-center[1]);
  } else {
   // UIKit/Android already draws the touch button. Keep the action verb only.
   for(unsigned v=0;v<4;++v){positions[q*12+v*3]=target[0];positions[q*12+v*3+1]=target[1];}
  }
 }
 return true;
}
}
