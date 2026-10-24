// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <cmath>
#include <vector>
namespace RetunedDeko {
struct Rect {int x,y,width,height;};
// GUI vertices are projected from DisplaySize into the actual render target.
// SDL's reported drawable scale can differ on an emulator/external context;
// using it for clips alone cuts off controls whose vertices rendered correctly.
inline Rect GuiClip(int width,int height,float displayX,float displayY,
                    float displayWidth,float displayHeight,
                    float left,float top,float right,float bottom) {
 if(width<=0||height<=0||displayWidth<=0||displayHeight<=0)return {0,0,0,0};
 const float sx=width/displayWidth,sy=height/displayHeight;
 const int x0=int(std::clamp(std::floor((left-displayX)*sx),0.f,float(width)));
 const int y0=int(std::clamp(std::floor((top-displayY)*sy),0.f,float(height)));
 const int x1=int(std::clamp(std::ceil((right-displayX)*sx),0.f,float(width)));
 const int y1=int(std::clamp(std::ceil((bottom-displayY)*sy),0.f,float(height)));
 return {x0,y0,std::max(0,x1-x0),std::max(0,y1-y0)};
}
// Partition the outside of an exclusive-end rectangle without double-drawing
// any pixel. This preserves blending and stencil semantics for PICA exclude.
inline std::vector<Rect> ExcludeRect(int width,int height,int x0,int y0,int x1,int y1) {
 x0=std::clamp(x0,0,width);x1=std::clamp(x1,0,width);
 y0=std::clamp(y0,0,height);y1=std::clamp(y1,0,height);
 if(x1<=x0||y1<=y0)return {{0,0,width,height}};
 std::vector<Rect> result;
 auto add=[&](int x,int y,int w,int h){if(w>0&&h>0)result.push_back({x,y,w,h});};
 add(0,0,width,y0);add(0,y1,width,height-y1);
 add(0,y0,x0,y1-y0);add(x1,y0,width-x1,y1-y0);
 return result;
}
}
