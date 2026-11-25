#include "a32_vfp_binary64.h"
#include <bit>
#include <cmath>
#include <iostream>
#include <stdexcept>
using namespace oot3d::recomp::a32;
void put(GuestState& s,unsigned d,double value){auto bits=std::bit_cast<std::uint64_t>(value);s.vfp[d*2]=bits;s.vfp[d*2+1]=bits>>32;}
double get(GuestState& s,unsigned d){return std::bit_cast<double>(std::uint64_t(s.vfp[d*2])|(std::uint64_t(s.vfp[d*2+1])<<32));}
void check(bool ok){if(!ok)throw std::runtime_error("VFP negated arithmetic failed");}
int main(){
    for(auto raw:{0xee137b08u,0xee137b48u,0xee237b48u}){
        GuestState s;put(s,7,5);put(s,3,2);put(s,8,3);s.cpsr=0xa0000010;
        check(VfpBinary64Supported(raw));auto result=ExecuteVfpBinary64(raw,0x1000,s);
        check(result.kind==ExitKind::Fallthrough && s.cpsr==0xa0000010);
        check(get(s,7)==(raw==0xee137b08?1:raw==0xee137b48?-11:-6));
    }
    GuestState s;put(s,7,0);put(s,3,0);put(s,8,INFINITY);
    ExecuteVfpBinary64(0xee137b08,0x1000,s);check(std::isnan(get(s,7)) && (s.fpscr&1));
    s={};put(s,3,0);put(s,8,3);ExecuteVfpBinary64(0xee237b48,0x1000,s);check(get(s,7)==0 && std::signbit(get(s,7)));
    check(!VfpBinary64Supported(0xee137b28)); // D24 is outside this guest ABI.
    std::cout<<"Negated VFP operations, signed zero, invalid exceptions, and register limits passed\n";
}
