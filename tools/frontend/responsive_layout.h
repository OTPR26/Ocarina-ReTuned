// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include "interface_metrics.h"
namespace RetunedFrontend {
inline float InterfaceScale(float height) { return std::clamp(height / 720.f, .75f, 1.5f); }
inline float NavigationWidth(float width,float font) { return std::min(width*.27f,font*12); }
}
