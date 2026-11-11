/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "hud_preset.h"
#include "hid.h"

static uint32_t sPreset;

uint32_t HudPreset_Get(void) { return sPreset; }
void HudPreset_Set(uint32_t preset) {
    if (preset <= 1) sPreset = preset;
}
uint32_t HudPreset_Button(ControlAction action) {
    switch (action) {
    case CONTROL_ACTION_ITEM_I: return sPreset ? BUTTON_UP : BUTTON_LEFT;
    case CONTROL_ACTION_ITEM_II: return BUTTON_DOWN;
    case CONTROL_ACTION_NAVI: return sPreset ? BUTTON_RIGHT : BUTTON_UP;
    case CONTROL_ACTION_OCARINA: return sPreset ? BUTTON_LEFT : BUTTON_RIGHT;
    default: return 0;
    }
}
