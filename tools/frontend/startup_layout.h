// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
namespace RetunedFrontend {
struct StartupMenuLayout {
 float Width, Height, Gap, Top, TextScale;
 bool ShowSetup;
};
inline StartupMenuLayout StartupLayout(float width,float height,float unit,float font,bool mobile,bool gameReady,float labelWidth=0) {
 const float gap=12.f*unit;
 const float footer=56.f*unit;
 const float top=height*.32f;
 const float available=std::max(0.f,(height-footer-top-2*gap)/3);
 const float button=std::min(54.f*unit,available);
 const float menuHeight=3*button+2*gap;
 const float menuWidth=std::min(width*.44f,428.f*unit);
 const float textScale=std::min(32.f*unit/font,std::max(1.f,(button-12.f*unit)/font));
 const float fitted=labelWidth>0?std::min(textScale,std::max(.5f,(menuWidth-24.f*unit)/labelWidth)):textScale;
 return {menuWidth,button,gap,std::max(top,height-footer-menuHeight),fitted,!gameReady};
}
}
