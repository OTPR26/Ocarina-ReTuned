/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef RETUNED_SCREEN_PRESENTATION_H
#define RETUNED_SCREEN_PRESENTATION_H

/* Host bridge v1: 0 = Single, 1 = Dual. Invalid requests never change state.
 * Called between guest updates, never from another rendering thread. */
unsigned ScreenPresentation_GetMode(void);
unsigned ScreenPresentation_TrySetMode(unsigned mode);
unsigned ScreenPresentation_IsDual(void);

#endif
