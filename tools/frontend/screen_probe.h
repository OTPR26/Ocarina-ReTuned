// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "retuned_screen_layout.h"
#include "duo_game_display.h"
#include <cstdlib>
#if defined(__APPLE__)
#include <TargetConditionals.h>
#endif
#include <cstdint>
#include <string_view>
#include <atomic>
namespace RetunedFrontend {
inline std::atomic<bool> ProbeGuestBridgeBound{false};
inline std::atomic<bool> ProbeGuestDualActive{false};
// Desktop arrangements remain diagnostic; mobile modes use device capabilities.
inline ScreenArrangement ScreenProbeArrangement() {
 if(ProbeGuestBridgeBound.load() && !ProbeGuestDualActive.load())return ScreenArrangement::Single;
 const char* value=std::getenv("RETUNED_SCREEN_PROBE");
 if(value && std::string_view(value)=="stacked")return ScreenArrangement::Stacked;
 if(value && std::string_view(value)=="side-by-side")return ScreenArrangement::SideBySide;
 return ScreenArrangement::Single;
}
inline bool DuoProbeRequested() {
#if defined(__APPLE__) && TARGET_OS_IOS && !TARGET_OS_TV
 return true;
#endif
 const char* value=std::getenv("RETUNED_SCREEN_PROBE");
 return value && std::string_view(value)=="duo";
}
inline bool ScreenProbeRequested(){return DuoProbeRequested() || ScreenProbeArrangement()!=ScreenArrangement::Single;}
inline bool ScreenProbeEnabled(){return (DuoProbeRequested() && DuoDisplay.Available()) || ScreenProbeArrangement()!=ScreenArrangement::Single;}
inline GameScreenLayout ScreenProbeLayout(float width,float height) {
 if(DuoProbeRequested())return DuoDisplay.Layout(width,height,ProbeGuestDualActive.load());
 // Input uses logical points, scanout uses drawable pixels: keep the gap relative.
 return LayoutGameScreens(width,height,ScreenProbeArrangement(),400.f/240.f,std::min(width,height)*.015f);
}
inline std::optional<LowerScreenTouch> ScreenProbeTouch(float width,float height,float x,float y) {
 if(DuoProbeRequested())return DuoDisplay.Touch(width,height,ProbeGuestDualActive.load(),x,y);
 return MapLowerScreenTouch(ScreenProbeLayout(width,height),x,y);
}
inline uint32_t ProbeOutputWidth(uint32_t width,uint32_t height) {
 return ScreenProbeEnabled()?std::max(1u,static_cast<uint32_t>(std::lround(ScreenProbeLayout(width,height).Top.Width))):width;
}
inline uint32_t ProbeOutputHeight(uint32_t width,uint32_t height) {
 return ScreenProbeEnabled()?std::max(1u,static_cast<uint32_t>(std::lround(ScreenProbeLayout(width,height).Top.Height))):height;
}
inline thread_local GameScreen ProbeScanoutScreen=GameScreen::Top;
struct ProbeScanoutScope {
 GameScreen Previous;
 explicit ProbeScanoutScope(GameScreen screen):Previous(ProbeScanoutScreen){ProbeScanoutScreen=screen;}
 ~ProbeScanoutScope(){ProbeScanoutScreen=Previous;}
};
}
