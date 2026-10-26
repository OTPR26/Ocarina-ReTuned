// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "android_display_state.h"
#include "retuned_shared_lower_equipment_runtime.h"
namespace RetunedFrontend {
inline void UpdateLowerEquipment(Oot3dNativeGame::NativeA32Process& process,bool hostMenu) {
 UpdateLowerEquipment(process,hostMenu,AndroidDualProbeRequested()&&AndroidGuestDualActive.load());
}
}
