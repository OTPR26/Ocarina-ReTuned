/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef RETUNED_MANUAL_JUMP_H
#define RETUNED_MANUAL_JUMP_H
#include "common.h"
#include "hid.h"
unsigned ManualJump_Get(void);
void ManualJump_Set(unsigned mode);
void ManualJump_Apply(GlobalContext*,pad_t*,volatile u32*,volatile u32*,volatile u32*,u32,u32,u32);
#endif
