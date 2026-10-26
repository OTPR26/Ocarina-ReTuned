#include <assert.h>
#include <string.h>
#include "manual_jump_fixture/common.h"
static unsigned pauseState=2,jumps;
#define MANUAL_JUMP_PAUSE_STATE pauseState
#define MANUAL_JUMP_START(player,context) (++jumps)
#include "../tools/reframed/manual_jump.c"
static Player player;
static GlobalContext context;
static pad_t pad;
static u32 held,pressed,released;
static void reset(void) {
 memset(&player,0,sizeof player);memset(&pad,0,sizeof pad);memset(&rInputCtx,0,sizeof rInputCtx);
 context.mainCamera.player=&player;gSaveContext.gameMode=0;gSaveContext.health=16;
 player.actor.bgCheckFlags=1;player.stateFuncPtr=0x004A34F0;
 items=save=ocarina=dead=0;pauseState=2;jumps=held=pressed=released=0;
}
static void apply(u32 zr,u32 zp,u32 zu) {ManualJump_Apply(&context,&pad,&held,&pressed,&released,zr,zp,zu);}
int main(void) {
 reset();ManualJump_Set(0);apply(IRRST_BUTTON_ZR,IRRST_BUTTON_ZR,0);assert(jumps==0);
 reset();ManualJump_Set(1);apply(IRRST_BUTTON_ZR,IRRST_BUTTON_ZR,0);assert(jumps==1);
 apply(IRRST_BUTTON_ZR,0,0);assert(jumps==1);
 for(int reason=0;reason<10;++reason) {
  reset();ManualJump_Set(1);
  switch(reason) {
   case 0:items=1;break;case 1:save=1;break;case 2:ocarina=1;break;case 3:dead=1;break;
   case 4:pauseState=3;break;case 5:gSaveContext.health=0;break;
   case 6:player.actor.bgCheckFlags=0;break;case 7:player.stateFuncPtr=0x004BBA4C;break;
   case 8:((u8*)&player)[0x12bc]=1;break;
   case 9:rInputCtx.cur.val=BUTTON_L1|BUTTON_R1;break;
  }
  apply(IRRST_BUTTON_ZR,IRRST_BUTTON_ZR,0);assert(jumps==0);
 }
 reset();ManualJump_Set(2);rInputCtx.cur.val=rInputCtx.pressed.val=BUTTON_X;
 pad.curr.val=pad.pressed.val=held=pressed=BUTTON_X;apply(0,0,0);
 assert(jumps==1&&!(held&BUTTON_X)&&!(pressed&BUTTON_X)&&!(pad.curr.val&BUTTON_X));
 apply(IRRST_BUTTON_ZR,IRRST_BUTTON_ZR,0);assert(held&BUTTON_X);assert(pressed&BUTTON_X);
 pressed=pad.pressed.val=rInputCtx.pressed.val=0;apply(0,0,IRRST_BUTTON_ZR);assert(!(held&BUTTON_X));assert(released&BUTTON_X);
 reset();ManualJump_Set(2);items=1;held=pressed=BUTTON_X;rInputCtx.cur.val=rInputCtx.pressed.val=BUTTON_X;
 apply(0,0,0);assert(held==BUTTON_X&&pressed==BUTTON_X&&jumps==0);
}
