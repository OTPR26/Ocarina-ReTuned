// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <atomic>
namespace RetunedFrontend {
inline std::atomic<bool> LowerEquipmentPanelEnabled{true};
inline std::atomic<bool> NativeLowerUiReady{false};
inline std::atomic<unsigned> LowerEquipmentState{0},LowerEquipmentRequest{0};
inline std::atomic<unsigned> LowerEquipmentSurfaceWidth{0},LowerEquipmentSurfaceHeight{0};
}
