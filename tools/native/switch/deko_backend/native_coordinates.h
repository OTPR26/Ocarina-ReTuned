// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
namespace RetunedDeko {
// ReFramed/PICA supplies bottom-left viewports and inclusive scissors.
// Reflect the origin while preserving size; changing scanout UVs would also
// mirror the contents of each correctly oriented panel.
template<class T> constexpr T TopLeftY(T targetHeight, T bottom, T height) {
    return targetHeight - bottom - height;
}
}
