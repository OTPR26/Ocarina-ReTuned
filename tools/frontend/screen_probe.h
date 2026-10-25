// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "retuned_screen_layout.h"
#include <cstdlib>
#include <cstdint>
#include <string_view>
#include <atomic>
namespace RetunedFrontend {
inline std::atomic<bool> ProbeGuestBridgeBound{false};
inline std::atomic<bool> ProbeGuestDualActive{false};
// Developer opt-in only. This does not enable an untested public screen-mode
// setting or claim that a prepared Single Screen mod has Dual Screen semantics.
inline ScreenArrangement ScreenProbeArrangement() {
 if(ProbeGuestBridgeBound.load() && !ProbeGuestDualActive.load())return ScreenArrangement::Single;
 const char* value=std::getenv("RETUNED_SCREEN_PROBE");
 if(value && std::string_view(value)=="stacked")return ScreenArrangement::Stacked;
 if(value && std::string_view(value)=="side-by-side")return ScreenArrangement::SideBySide;
 return ScreenArrangement::Single;
}
inline bool ScreenProbeEnabled(){return ScreenProbeArrangement()!=ScreenArrangement::Single;}
inline GameScreenLayout ScreenProbeLayout(float width,float height) {
 // Input uses logical points, scanout uses drawable pixels: keep the gap relative.
 return LayoutGameScreens(width,height,ScreenProbeArrangement(),400.f/240.f,std::min(width,height)*.015f);
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
