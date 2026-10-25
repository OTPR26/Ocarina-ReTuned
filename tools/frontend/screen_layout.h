// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <cmath>
#include <optional>

namespace RetunedFrontend {
enum class ScreenArrangement { Single, Stacked, SideBySide };
enum class GameScreen { Top, Lower };
struct ScreenRect {
 float X=0, Y=0, Width=0, Height=0;
 bool Contains(float x,float y) const {
  return Width>0 && Height>0 && x>=X && y>=Y && x<X+Width && y<Y+Height;
 }
};
struct GameScreenLayout { ScreenRect Top, Lower; };
inline ScreenRect FitScreen(ScreenRect bounds,float aspect) {
 if(!std::isfinite(aspect)||aspect<=0 || bounds.Width<=0 || bounds.Height<=0)return {};
 const float width=std::min(bounds.Width,bounds.Height*aspect),height=width/aspect;
 return {bounds.X+(bounds.Width-width)*.5f,bounds.Y+(bounds.Height-height)*.5f,width,height};
}
// Both outputs share one guest update. These rectangles are presentation and
// input coordinates only; they never change native framebuffer dimensions.
inline GameScreenLayout LayoutGameScreens(float width,float height,ScreenArrangement mode,
                                          float topAspect=400.f/240.f,float gap=12.f) {
 if(!std::isfinite(width)||!std::isfinite(height)||width<=0||height<=0||
    !std::isfinite(gap)||gap<0||!std::isfinite(topAspect)||topAspect<=0)return {};
 if(mode==ScreenArrangement::Single)return {FitScreen({0,0,width,height},topAspect),{}};
 constexpr float lowerAspect=320.f/240.f;
 if(mode==ScreenArrangement::Stacked) {
  gap=std::min(gap,height);
  const float h=std::min((height-gap)*.5f,width/std::max(topAspect,lowerAspect));
  const float y=(height-2*h-gap)*.5f;
  return {{(width-h*topAspect)*.5f,y,h*topAspect,h},
          {(width-h*lowerAspect)*.5f,y+h+gap,h*lowerAspect,h}};
 }
 gap=std::min(gap,width);
 const float h=std::min(height,(width-gap)/(topAspect+lowerAspect));
 const float x=(width-h*(topAspect+lowerAspect)-gap)*.5f,y=(height-h)*.5f;
 return {{x,y,h*topAspect,h},{x+h*topAspect+gap,y,h*lowerAspect,h}};
}
struct LowerScreenTouch {unsigned X,Y;};
inline std::optional<LowerScreenTouch> MapLowerScreenTouch(const GameScreenLayout& layout,float x,float y) {
 if(!std::isfinite(x)||!std::isfinite(y)||!layout.Lower.Contains(x,y))return {};
 return LowerScreenTouch{
  std::min(319u,static_cast<unsigned>((x-layout.Lower.X)/layout.Lower.Width*320.f)),
  std::min(239u,static_cast<unsigned>((y-layout.Lower.Y)/layout.Lower.Height*240.f))};
}
}
