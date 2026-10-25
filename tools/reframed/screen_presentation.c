/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "screen_presentation.h"

/* The mod supplies this predicate using its existing menu/transition state.
 * Keeping it separate also permits the protocol to be tested on the host. */
extern unsigned ScreenPresentation_CanSwitch(void);
static unsigned sScreenMode;

unsigned ScreenPresentation_GetMode(void) { return sScreenMode; }
unsigned ScreenPresentation_IsDual(void) { return sScreenMode == 1; }

unsigned ScreenPresentation_TrySetMode(unsigned mode) {
    if (mode > 1) return 0;
    if (mode == sScreenMode) return 1;
    if (!ScreenPresentation_CanSwitch()) return 0;
    sScreenMode = mode;
    return 1;
}
