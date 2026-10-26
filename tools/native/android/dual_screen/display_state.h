// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <atomic>
#include <cstdlib>
#include <string_view>
#include "lower_equipment_state.h"
namespace RetunedFrontend {
inline std::atomic<bool> AndroidLowerAvailable{false}, AndroidDualSelected{true}, AndroidGuestDualActive{false};
inline std::atomic<unsigned> AndroidLowerTouch{0};
inline std::atomic<unsigned> AndroidLowerWidth{0},AndroidLowerHeight{0};
inline auto& AndroidEquipmentState=LowerEquipmentState;
inline auto& AndroidEquipmentRequest=LowerEquipmentRequest;
inline bool AndroidDualProbeRequested() {
 const char* v=std::getenv("RETUNED_SCREEN_PROBE");return v&&std::string_view(v)=="android-dual";
}
}
