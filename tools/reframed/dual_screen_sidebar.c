/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "screen_presentation.h"

/* Canonical EUR native item-label renderer. These calls contain only the
 * four controller glyphs, not equipped items or quantities. Keep the native
 * draw in Single; the Dual sidebar uses the same icon-only treatment as
 * ReMasked. No geometry, input state or shared texture is modified. */
void ScreenPresentation_DrawItemLabels(void* labels) {
    if (!ScreenPresentation_IsDual())
        ((void (*)(void*))0x002FB934)(labels);
}

/* The sword's B badge is a separate quad in the native gameplay panel.
 * Collapse only its submitted geometry, restoring it immediately afterward.
 * The sword, action text, quantities, and touch rectangles are separate. */
void ScreenPresentation_SubmitSidebar(void) {
    void* board = *(void**)0x0050AF38;
    float saved[12];
    float* badge = 0;
    if (ScreenPresentation_IsDual() && board && *(unsigned*)board == 92) {
        float* positions = *(float**)((unsigned char*)board + 0x0c);
        if (positions) {
            badge = positions + 34 * 12;
            for (unsigned i = 0; i < 12; ++i) saved[i] = badge[i];
            for (unsigned v = 1; v < 4; ++v)
                for (unsigned axis = 0; axis < 3; ++axis)
                    badge[v * 3 + axis] = badge[axis];
        }
    }
    ((void (*)(void))0x0042DDA8)();
    if (badge)
        for (unsigned i = 0; i < 12; ++i) badge[i] = saved[i];
}
