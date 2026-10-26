// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "fast/oot3d/lower_equipment_state.h"
#include <cstdio>
#include "oot3d_native_a32_process.h"
#include "fast/oot3d/retuned_lower_equipment.h"
#include "oot3d_top_screen_gameplay_action_consumer.h"
namespace RetunedFrontend {
inline void UpdateLowerEquipment(Oot3dNativeGame::NativeA32Process& process,bool hostMenu,bool dual) {
 const unsigned request=LowerEquipmentRequest.exchange(0);
 if(!LowerEquipmentPanelEnabled.load()||!dual){LowerEquipmentState=0;return;}
 auto& m=process.Memory();
 constexpr unsigned save=0x00587958;
 unsigned age=1,quest=0,pause=0,play=0,player=0;
 uint16_t owned=0,equipped=0,health=0;uint8_t pulse=255,type=0,subtype=0;
 if(!m.Read32(save+4,&age)||!m.Read32(save+0xbc,&quest)||
    !m.Read16(save+0xb6,&owned)||!m.Read16(save+0x8a,&equipped)||
    !m.Read16(save+0x44,&health)||!m.Read32(0x0050af68,&pause)||
    !m.Read32(0x005043e0,&play)||!play||!m.IsMapped(play,0x20b0)||
    !m.Read32(play+0x20ac,&player)||!player||!m.IsMapped(player,0x12bd)||
    !m.Read8(play+0x100,&type)||!m.Read8(play+0x101,&subtype)){LowerEquipmentState=0;return;}
 // Read the original Shard HUD animation counter, reset by the native
 // detection path. No host timer or proximity approximation is involved.
 m.Read8(0x004fc649,&pulse);
 const bool ready=!hostMenu&&health&&pause==2&&type==3&&subtype==2;
 LowerEquipmentState=PackLowerEquipment(ready,age==0,owned,equipped,
                                         (quest&(1u<<21))!=0,pulse) | ((health&&type==3&&subtype==2)?(1u<<14):0u);
 if(!ready||age!=0||(request!=1&&request!=2))return;
 Oot3dNativeGame::TopScreenDpadActionState actions;
 const auto action=request==1?Oot3dNativeGame::TopScreenDpadAction::AllBootsToggle:
                             Oot3dNativeGame::TopScreenDpadAction::TunicToggle;
 actions.Pressed[static_cast<unsigned>(action)]=true;
 Oot3dNativeGame::TopScreenGameplayActionConsumerRuntime runtime;
 std::string error;
 if(!Oot3dNativeGame::ConsumeTopScreenGameplayActions(process,actions,false,0xffff0000,
       &runtime,nullptr,&error))
   std::fprintf(stderr,"RETUNED_LOWER_EQUIPMENT rejected: %s\n",error.c_str());
}
}
