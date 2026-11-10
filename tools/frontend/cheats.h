// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <mutex>
#include <string>
namespace RetunedFrontend {
struct CheatOptions {
 bool Health=false,Magic=false,Rupees=false;
 std::array<bool,6> Ammo{};
};
struct CheatAmmo { const char* Name; unsigned Slot,Item,Shift; std::array<int,4> Capacity; };
// OoT3D inventory slots and upgrade capacities, verified by ui_inventory_content.cpp.
inline constexpr std::array<CheatAmmo,6> CheatAmmunition{{
 {"Deku sticks",0,0,17,{0,10,20,30}}, {"Deku nuts",1,1,20,{0,20,30,40}},
 {"Bombs",2,2,3,{0,20,30,40}}, {"Arrows",3,3,0,{0,30,40,50}},
 {"Deku seeds",6,6,14,{0,30,40,50}}, {"Bombchus",8,9,0,{50,50,50,50}}
}};
struct CheatSnapshot {
 bool Ready=false; uint32_t Save=0,File=0,Entrance=0;
 int Rupees=0,Wallet=0; std::array<int,6> Ammo{},Capacity{};
};
struct CheatEdit { bool Pending=false; CheatSnapshot Origin{}; int Rupees=-1; std::array<int,6> Ammo{-1,-1,-1,-1,-1,-1}; };
struct CheatState {
 std::mutex Mutex; CheatOptions Options; CheatSnapshot Snapshot; CheatEdit Edit; std::string Message;
};
inline CheatState Cheats;
inline void InvalidateCheats() {
 std::lock_guard lock(Cheats.Mutex);
 Cheats.Snapshot={};Cheats.Edit={};
}
inline int CheatAmmoCapacity(unsigned index,uint8_t item,uint32_t upgrades) {
 const auto& a=CheatAmmunition[index];
 if(item!=a.Item)return 0;
 unsigned level=index==5?0:((upgrades>>a.Shift)&7);
 return level<4?a.Capacity[level]:0;
}
template<class Memory> void UpdateCheats(Memory& m,uint32_t save,bool eligible) {
 std::lock_guard lock(Cheats.Mutex);
 auto edit=Cheats.Edit; Cheats.Edit={}; Cheats.Snapshot={};
 auto reject=[&](){if(edit.Pending)Cheats.Message="Could not apply changes here. Try again during normal gameplay.";};
 if(!eligible){reject();return;}
 uint16_t health=0,maximum=0,money=0; uint32_t upgrades=0,mode=1,file=0,entrance=0;
 uint8_t level=0,magic=0,acquired=0; uint16_t rupeeChange=0;
 if(!m.Read16(save+0x44,&health)||!m.Read16(save+0x42,&maximum)||
    !m.Read16(save+0x48,&money)||!m.Read32(save+0xb8,&upgrades)||
    !m.Read32(save+0x14e4,&mode)||!m.Read32(save+0x14dc,&file)||
    !m.Read32(save,&entrance)||!m.Read8(save+0x46,&level)||
    !m.Read8(save+0x47,&magic)||!m.Read8(save+0x4e,&acquired)||
    !m.Read16(save+0x155c,&rupeeChange)||mode!=0||file>2||
    !health||maximum<0x30||maximum>0x140||health>maximum){reject();return;}
 CheatSnapshot state; state.Ready=true;state.Save=save;state.File=file;state.Entrance=entrance;
 state.Rupees=money; constexpr int wallets[]{99,200,500,500};state.Wallet=wallets[(upgrades>>12)&3];
 for(unsigned i=0;i<CheatAmmunition.size();++i){
  uint8_t item=0xff,ammo=0;const auto slot=CheatAmmunition[i].Slot;
  if(!m.Read8(save+0x8c+slot,&item)||!m.Read8(save+0xa6+slot,&ammo)){reject();return;}
  state.Ammo[i]=ammo;state.Capacity[i]=CheatAmmoCapacity(i,item,upgrades);
 }
 bool apply=edit.Pending&&edit.Origin.Save==save&&edit.Origin.File==file&&edit.Origin.Entrance==entrance;
 bool ok=true;
 const auto options=Cheats.Options;
 if(options.Health)ok=m.Write16(save+0x44,maximum)&&ok;
 if(options.Magic&&acquired==1&&level>=1&&level<=2)ok=m.Write8(save+0x47,uint8_t(level*48))&&ok;
 // Let the native purchase/pickup animation finish before changing the wallet.
 if(!rupeeChange&&(options.Rupees||(apply&&edit.Rupees>=0))){
  state.Rupees=options.Rupees?state.Wallet:std::clamp(edit.Rupees,0,state.Wallet);
  ok=m.Write16(save+0x48,uint16_t(state.Rupees))&&ok;
 }else if(apply&&edit.Rupees>=0&&!options.Rupees)ok=false;
 for(unsigned i=0;i<CheatAmmunition.size();++i)if(state.Capacity[i]>0&&(options.Ammo[i]||(apply&&edit.Ammo[i]>=0))){
  state.Ammo[i]=options.Ammo[i]?state.Capacity[i]:std::clamp(edit.Ammo[i],0,state.Capacity[i]);
  ok=m.Write8(save+0xa6+CheatAmmunition[i].Slot,uint8_t(state.Ammo[i]))&&ok;
 }
 Cheats.Snapshot=state;
 if(edit.Pending)Cheats.Message=apply?(ok?"Changes applied. Save in game to keep them.":"Some changes could not be applied. Refresh amounts and try again."):"The game changed scenes or saves. Refresh amounts and try again.";
}
}
