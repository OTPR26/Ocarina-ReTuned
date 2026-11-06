/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef RETUNED_MINIMAP_TOGGLE_H
#define RETUNED_MINIMAP_TOGGLE_H

/* Canonical native image: use the same availability check and toggle as
 * the game's D-pad path. The toggle owns visibility and its sound effect. */
#ifndef RETUNED_MINIMAP_AVAILABLE
#define RETUNED_MINIMAP_AVAILABLE() (((unsigned (*)(void))0x002F00F4)())
#define RETUNED_MINIMAP_TOGGLE() (((void (*)(void))0x002F009C)())
#endif

static inline void RetunedMinimap_Update(unsigned pressed, unsigned gameplay) {
    if (gameplay && (pressed & (1u << 14)) && RETUNED_MINIMAP_AVAILABLE())
        RETUNED_MINIMAP_TOGGLE();
}
#endif
