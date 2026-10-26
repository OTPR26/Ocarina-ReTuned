#pragma once
#include "common.h"
typedef struct {u32 val;} btn_t;
typedef struct {btn_t curr,pressed,released;} pad_t;
#define BUTTON_X (1u<<10)
#define BUTTON_L1 (1u<<9)
#define BUTTON_R1 (1u<<8)
#define IRRST_BUTTON_ZR (1u<<15)
