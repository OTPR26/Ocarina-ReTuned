// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <imgui.h>
namespace RetunedFrontend {
inline bool RefreshMenuGamepads(int count,int& previous,unsigned now,unsigned& last,bool ready) {
 const bool refresh=count!=previous || (count>0 && !ready && unsigned(now-last)>=250);
 previous=count;if(refresh)last=now;return refresh;
}
inline ImGuiWindowFlags GameCanvasFlags(ImGuiWindowFlags flags) {
 return flags|ImGuiWindowFlags_NoNav|ImGuiWindowFlags_NoFocusOnAppearing|ImGuiWindowFlags_NoBringToFrontOnFocus;
}
inline bool MenuBackClosesSettings(bool back,bool popupBefore,bool editingBefore,bool popupNow) {
 return back && !popupBefore && !editingBefore && !popupNow;
}
inline bool RemoteBackTogglesSettings(bool startup,bool settings,bool popup,bool editing) {
 return (!startup || settings) && !popup && !editing;
}
inline void EnableMenuNavigation(bool television) {
 auto& io=ImGui::GetIO();
 io.ConfigFlags|=ImGuiConfigFlags_NavEnableKeyboard|ImGuiConfigFlags_NavEnableGamepad;
 if(television) {
  io.ConfigNavCursorVisibleAlways=true;
  ImGui::SetNavCursorVisible(true);
 }
}
}
