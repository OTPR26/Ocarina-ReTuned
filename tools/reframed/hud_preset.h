/* SPDX-License-Identifier: GPL-2.0-or-later */
#pragma once
#include "controls.h"
#include <stdint.h>

uint32_t HudPreset_Get(void);
void HudPreset_Set(uint32_t preset);
uint32_t HudPreset_Button(ControlAction action);
