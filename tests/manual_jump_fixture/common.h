#pragma once
#include <stdint.h>
typedef uint32_t u32;typedef uint8_t u8;
typedef struct {struct {u32 bgCheckFlags;} actor;void* heldActor;u32 stateFuncPtr;u8 reserved[0x2400];} Player;
typedef struct {struct {Player* player;} mainCamera;} GlobalContext;
static struct {int gameMode,health;} gSaveContext;
