// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstdint>
namespace RetunedFrontend {
inline bool LowerUiSettled(unsigned pause, bool sceneSettled, bool saveDialog) {
    return sceneSettled && (pause==2 || pause==12 || pause==16 || pause==20 || saveDialog);
}
template<class Memory> bool HideNativeSaveOptions(Memory& memory) {
    uint32_t board=0,count=0,colors=0;
    if (!memory.Read32(0x0050A510,&board) || !board ||
        !memory.Read32(board,&count) || count!=78 ||
        !memory.Read32(board+0x18,&colors) || !colors ||
        !memory.IsWritable(colors+18*64,4*64)) return false;
    // The native Save board owns these four Options-button quads. Preserve
    // its other geometry, animation, confirmations, and save-writing logic.
    for (unsigned quad=18;quad<=21;++quad)
        for (unsigned vertex=0;vertex<4;++vertex)
            if (!memory.Write32(colors+quad*64+vertex*16+12,0)) return false;
    return true;
}
}
