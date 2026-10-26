// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
namespace RetunedFrontend {
struct LowerEquipmentLayout {
 float PictureWidth=0,PictureHeight=0,StripHeight=0,PictureY=0;
};
inline LowerEquipmentLayout LayoutLowerEquipment(float width,float height,bool panel=true) {
 if(!std::isfinite(width)||!std::isfinite(height)||width<=0||height<=0)return {};
 const float w=std::min(width,height*4.f/3.f),h=w*3.f/4.f;
 return {w,h,panel?height-h:0,panel?0:(height-h)*.5f};
}
// Native detection pulses last sixteen game updates. Ownership is required;
// an uninitialized animation counter must never reveal an unowned secret.
inline bool LowerAgonyPulse(bool owned,unsigned nativeFrame) {
 return owned && nativeFrame<16;
}
inline unsigned PackLowerEquipment(bool ready,bool adult,unsigned owned,unsigned equipped,
                                  bool agonyOwned,unsigned agonyFrame) {
 return unsigned(ready&&adult) | (unsigned(agonyOwned)<<1) |
   (unsigned(ready&&LowerAgonyPulse(agonyOwned,agonyFrame))<<2) | (unsigned(adult)<<3) |
   (((equipped>>12)&3)<<4) | (((equipped>>8)&3)<<6) |
   (((owned>>12)&7)<<8) | (((owned>>8)&7)<<11);
}
}
