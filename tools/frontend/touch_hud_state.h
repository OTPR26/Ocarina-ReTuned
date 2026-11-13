// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "touch_hud_model.h"
#include <mutex>
#include <atomic>
namespace RetunedFrontend {
inline std::atomic<int> TouchManualJumpMode{0};
inline std::atomic<int> TouchHudPreset{0};
inline std::mutex TouchHudMutex;
inline TouchHudAnchors TouchHudLayout;
inline std::atomic<bool> TouchHudRequested{true},TouchHudActive{false};
inline std::atomic<bool> TouchHudLive{false};
inline std::atomic<float> TouchIconOpacity{1.f};
inline std::atomic<float> TouchHudAspect{400.f/240.f};
inline void SetTouchHudDisplay(float width,float height) {
 if(std::isfinite(width)&&std::isfinite(height)&&width>0&&height>0)TouchHudAspect=width/height;
}
inline void SetTouchHudAnchor(int slot,float x,float y) {
 if(slot<0||slot>=9)return;
 std::lock_guard lock(TouchHudMutex);TouchHudLayout[slot]={x,y,true,TouchHudLayout[slot].Scale};
}
inline void SetTouchHudScale(int slot,float scale){
 if(slot<0||slot>=9||!std::isfinite(scale))return;
 std::lock_guard lock(TouchHudMutex);TouchHudLayout[slot].Scale=std::clamp(scale,.5f,1.5f);
}
inline TouchHudAnchors SnapshotTouchHud(){std::lock_guard lock(TouchHudMutex);return TouchHudLayout;}
}
