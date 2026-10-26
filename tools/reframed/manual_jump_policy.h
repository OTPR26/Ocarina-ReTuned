/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef RETUNED_MANUAL_JUMP_POLICY_H
#define RETUNED_MANUAL_JUMP_POLICY_H
/* Platform-independent input policy. Native safety checks happen separately. */
static inline unsigned ManualJump_ValidMode(unsigned mode) {
    return mode <= 2 ? mode : 0;
}

static inline int ManualJump_Pressed(unsigned mode, int gameplay, int chord,
                                     int xPressed, int zrPressed) {
    if (!gameplay || chord) return 0;
    if (mode == 1) return zrPressed;
    if (mode == 2) return xPressed;
    return 0;
}

static inline unsigned ManualJump_ItemMask(unsigned mode, int gameplay,
                                           unsigned original, unsigned xMask, int zr) {
    if (mode != 2 || !gameplay) return original;
    return (original & ~xMask) | (zr ? xMask : 0);
}
#endif
