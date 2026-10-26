#include "../tools/frontend/lower_equipment.h"
#include <cassert>
#include <limits>
int main(){
 using namespace RetunedFrontend;
 auto l=LayoutLowerEquipment(1240,1080);
 assert(l.PictureWidth==1240&&l.PictureHeight==930&&l.StripHeight==150);
 auto centered=LayoutLowerEquipment(1240,1080,false);
 assert(centered.PictureY==75&&centered.StripHeight==0);
 assert(LayoutLowerEquipment(0,1080).StripHeight==0);
 assert(LayoutLowerEquipment(std::numeric_limits<float>::infinity(),1080).PictureWidth==0);
 assert(!LowerAgonyPulse(false,0));assert(LowerAgonyPulse(true,0));
 assert(LowerAgonyPulse(true,15));assert(!LowerAgonyPulse(true,16));
 auto s=PackLowerEquipment(true,true,0x7700,0x2300,true,3);
 assert((s&7)==7&&((s>>4)&3)==2&&((s>>6)&3)==3);
 assert(((s>>8)&7)==7&&((s>>11)&7)==7);
 assert(!(PackLowerEquipment(true,false,0,0,false,0)&1));
 assert(!(PackLowerEquipment(false,true,0,0,true,0)&5));
}
