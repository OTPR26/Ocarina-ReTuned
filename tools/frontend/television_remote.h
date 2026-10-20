// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cmath>
namespace RetunedFrontend {
struct TelevisionRemoteButtons { bool Up,Down,Left,Right,Accept,Back; };
inline TelevisionRemoteButtons RemoteButtons(float x,float y,bool click,bool back) {
 const bool horizontal=std::isfinite(x)&&std::abs(x)>.5f;
 const bool vertical=std::isfinite(y)&&std::abs(y)>.5f;
 return {vertical&&y>0,vertical&&y<0,horizontal&&x<0,horizontal&&x>0,click&&!horizontal&&!vertical,back};
}
}
