// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
namespace RetunedFrontend {
struct StartupMenuLayout {
 float Width, Height, Gap, Top, TextScale;
 bool ShowSetup;
};
inline StartupMenuLayout StartupLayout(float width,float height,float unit,float font,bool mobile,bool gameReady) {
 const float gap=(mobile?10.f:6.f)*unit;
 const float footer=56.f*unit;
 const float top=height*.32f;
 const float available=std::max(0.f,(height-footer-top-2*gap)/3);
 const float button=std::min(std::max(font*2.2f,(mobile?64.f:44.f)*unit),available);
 const float menuHeight=3*button+2*gap;
 return {std::min(width*.44f,font*24),button,gap,
         std::max(top,height-footer-menuHeight),mobile?1.3f:1.f,!gameReady};
}
}
