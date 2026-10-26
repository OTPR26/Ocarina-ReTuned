/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "manual_jump.h"
#include "manual_jump_policy.h"
#include "input.h"
#include "input_consume.h"
#include "input_remap.h"
#ifndef MANUAL_JUMP_PAUSE_STATE
#define MANUAL_JUMP_PAUSE_STATE (*(volatile u32*)0x0050AF68)
#endif
#ifndef MANUAL_JUMP_START
#define MANUAL_JUMP_START(player,context) \
    ((JumpFn)0x0034B3DC)(player,0x95,context,0x010004EB,6.0f)
#endif
static unsigned sMode;
unsigned ManualJump_Get(void) {return sMode;}
void ManualJump_Set(unsigned mode) {sMode=ManualJump_ValidMode(mode);}

static int Gameplay(GlobalContext* context) {
    return context && gSaveContext.gameMode==0 && gSaveContext.health &&
        MANUAL_JUMP_PAUSE_STATE==2 &&
        !InputRemap_IsItemsMenuOpen() && !InputRemap_IsSaveMenuOpen() &&
        !InputRemap_IsOcarinaUiOpen() && !InputRemap_IsGameOverUiOpen();
}
static int Grounded(const Player* p) {
    if(!p || !(p->actor.bgCheckFlags&1) || p->heldActor ||
       *((const u8*)p+0x12bc) || *((const u8*)p+0x1a7)==1)return 0;
    const u32 action=(u32)p->stateFuncPtr;
    /* Normal idle/movement only. Mounted, climbing, swimming, rolling,
     * combat transitions and cutscene actions cannot start this jump. */
    return action==0x004BA378 || action==0x004A27BC || action==0x004A34F0;
}
void ManualJump_Apply(GlobalContext* context,pad_t* pad,volatile u32* held,
        volatile u32* pressed,volatile u32* released,u32 extra,u32 extraPress,u32 extraRelease) {
    if(!sMode || !Gameplay(context))return;
    /* Preserve configuration chords. A held button never queues a jump. */
    if((rInputCtx.cur.val&(BUTTON_L1|BUTTON_R1))==(BUTTON_L1|BUTTON_R1))return;
    const unsigned jump=ManualJump_Pressed(sMode,1,0,
        !!(rInputCtx.pressed.val&BUTTON_X),!!(extraPress&IRRST_BUTTON_ZR));
    if(sMode==2) {
        #define ITEM_MASK(value,zr) ManualJump_ItemMask(sMode,1,value,BUTTON_X,!!((zr)&IRRST_BUTTON_ZR))
        pad->curr.val=ITEM_MASK(pad->curr.val,extra);
        pad->pressed.val=ITEM_MASK(pad->pressed.val,extraPress);
        pad->released.val=ITEM_MASK(pad->released.val,extraRelease);
        *held=ITEM_MASK(*held,extra);*pressed=ITEM_MASK(*pressed,extraPress);
        *released=ITEM_MASK(*released,extraRelease);
        rInputCtx.cur.val=ITEM_MASK(rInputCtx.cur.val,extra);
        rInputCtx.pressed.val=ITEM_MASK(rInputCtx.pressed.val,extraPress);
        rInputCtx.up.val=ITEM_MASK(rInputCtx.up.val,extraRelease);
        #undef ITEM_MASK
    }
    Player* player=context->mainCamera.player;
    if(jump && Grounded(player)) {
        /* Canonical EUR/USA routine used by the native ledge-jump path:
         * switches to airborne movement, starts animation, clears ground,
         * initializes vertical speed and plays native jump sounds.
         * This callee takes its float in S0, unlike the mod's softfp ABI. */
        typedef void (*JumpFn)(Player*,int,GlobalContext*,u32,float) __attribute__((pcs("aapcs-vfp")));
        MANUAL_JUMP_START(player,context);
    }
}
