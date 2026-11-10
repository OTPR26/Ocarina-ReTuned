#include "../tools/frontend/cheats.h"
#include <cassert>
#include <vector>
using namespace RetunedFrontend;
struct Memory {
 std::array<uint8_t,0x2000> Data{};std::vector<unsigned> Writes;
 bool Read8(unsigned a,uint8_t* v){if(a>=Data.size())return false;*v=Data[a];return true;}
 bool Read16(unsigned a,uint16_t* v){if(a+1>=Data.size())return false;*v=Data[a]|unsigned(Data[a+1])<<8;return true;}
 bool Read32(unsigned a,uint32_t* v){if(a+3>=Data.size())return false;*v=0;for(int i=0;i<4;i++)*v|=unsigned(Data[a+i])<<(i*8);return true;}
 bool Write8(unsigned a,uint8_t v){if(a>=Data.size())return false;Data[a]=v;Writes.push_back(a);return true;}
 bool Write16(unsigned a,uint16_t v){if(a+1>=Data.size())return false;Data[a]=v;Data[a+1]=v>>8;Writes.push_back(a);return true;}
 void Word(unsigned a,uint32_t v){for(int i=0;i<4;i++)Data[a+i]=v>>(i*8);}
};
Memory Fixture(){
 Memory m;m.Write16(0x42,0xa0);m.Write16(0x44,0x60);m.Write16(0x48,10);
 m.Data[0x46]=1;m.Data[0x47]=8;m.Data[0x4e]=1;
 m.Word(0xb8,(1u<<17)|(1u<<20)|(1u<<3)|1u|(1u<<14));
 for(auto a:CheatAmmunition){m.Data[0x8c+a.Slot]=a.Item;m.Data[0xa6+a.Slot]=2;}
 m.Writes.clear();return m;
}
void Reset(){Cheats.Options={};Cheats.Edit={};Cheats.Snapshot={};Cheats.Message.clear();}
int main(){
 Reset();auto m=Fixture();auto original=m.Data;
 UpdateCheats(m,0,true);assert(m.Writes.empty()&&m.Data==original&&Cheats.Snapshot.Ready);
 assert(Cheats.Snapshot.Wallet==99&&Cheats.Snapshot.Capacity[5]==50);
 Cheats.Options.Health=true;Cheats.Options.Magic=true;Cheats.Options.Rupees=true;Cheats.Options.Ammo.fill(true);UpdateCheats(m,0,true);
 assert(m.Data[0x44]==0xa0&&m.Data[0x47]==48&&m.Data[0x48]==99);
 for(unsigned i=0;i<6;i++)assert(m.Data[0xa6+CheatAmmunition[i].Slot]==Cheats.Snapshot.Capacity[i]);
 // Ownership, equipment, upgrades, and progress flags must be untouched.
 for(unsigned i=0;i<m.Data.size();i++){
  bool resource=i==0x44||i==0x45||i==0x47||i==0x48||i==0x49;
  for(auto a:CheatAmmunition)resource|=i==0xa6+a.Slot;
  if(!resource)assert(m.Data[i]==original[i]);
 }
 m=Fixture();m.Data[0x4e]=0;m.Data[0x8c+8]=0xff;UpdateCheats(m,0,true);
 assert(m.Data[0x47]==8&&m.Data[0xa6+8]==2&&Cheats.Snapshot.Capacity[5]==0);
 m=Fixture();m.Data[0x46]=2;UpdateCheats(m,0,true);assert(m.Data[0x47]==96);
 m=Fixture();m.Write16(0x44,0);m.Writes.clear();UpdateCheats(m,0,true);assert(m.Writes.empty()&&!Cheats.Snapshot.Ready);
 m=Fixture();UpdateCheats(m,0,false);assert(m.Writes.empty());
 m=Fixture();m.Word(0x14e4,1);UpdateCheats(m,0,true);assert(m.Writes.empty());
 m=Fixture();m.Word(0x14dc,0xff);UpdateCheats(m,0,true);assert(m.Writes.empty());
 assert(CheatAmmoCapacity(0,0,7u<<17)==0);
 Reset();m=Fixture();UpdateCheats(m,0,true);
 Cheats.Edit.Pending=true;Cheats.Edit.Origin=Cheats.Snapshot;Cheats.Edit.Rupees=9999;Cheats.Edit.Ammo[3]=999;
 UpdateCheats(m,0,true);assert(m.Data[0x48]==99&&m.Data[0xa6+3]==30&&!Cheats.Edit.Pending);
 m.Writes.clear();UpdateCheats(m,0,true);assert(m.Writes.empty()); // Apply is one-shot.
 Cheats.Edit.Pending=true;Cheats.Edit.Origin=Cheats.Snapshot;Cheats.Edit.Rupees=0;m.Word(0,1);
 UpdateCheats(m,0,true);assert(m.Writes.empty()&&m.Data[0x48]==99);
 Cheats.Edit.Pending=true;Cheats.Edit.Origin=Cheats.Snapshot;Cheats.Edit.Rupees=0;m.Word(0x14dc,1);
 UpdateCheats(m,0,true);assert(m.Writes.empty());
 Cheats.Options.Rupees=true;m.Write16(0x155c,1);m.Writes.clear();UpdateCheats(m,0,true);assert(m.Writes.empty());
 m.Write16(0x155c,0);m.Word(0xb8,2u<<12);m.Writes.clear();UpdateCheats(m,0,true);
 uint16_t money=0;m.Read16(0x48,&money);assert(money==500);
 Reset();m=Fixture();UpdateCheats(m,0x1fff,true);assert(m.Writes.empty());
 // Each ammunition toggle is independent; turning it off stops refilling.
 Reset();m=Fixture();Cheats.Options.Ammo[3]=true;UpdateCheats(m,0,true);
 assert(m.Data[0xa6+3]==30&&m.Data[0xa6+2]==2&&m.Data[0x48]==10);
 Cheats.Options.Ammo[3]=false;m.Data[0xa6+3]=5;m.Writes.clear();UpdateCheats(m,0,true);
 assert(m.Data[0xa6+3]==5&&m.Writes.empty());
 Cheats.Options.Ammo[2]=true;Cheats.Edit.Pending=true;Cheats.Edit.Origin=Cheats.Snapshot;Cheats.Edit.Ammo[3]=12;
 UpdateCheats(m,0,true);assert(m.Data[0xa6+2]==20&&m.Data[0xa6+3]==12);
}
