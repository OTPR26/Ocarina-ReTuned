// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <stdexcept>
#include <string>
#include <string_view>

namespace RetunedSwitchShader {
inline void ReplaceOnce(std::string& source,std::string_view before,std::string_view after) {
 const auto at=source.find(before);
 if(at==std::string::npos || source.find(before,at+before.size())!=std::string::npos)
  throw std::runtime_error("Switch procedural shader arithmetic context changed");
 source.replace(at,before.size(),after);
}
// Mesa's signed constant division emits IMUL/IMAD instructions unsupported by
// the current emulator shader translator. Preserve truncation toward zero.
// For |value| <= 2^31 the float estimate is within 32 of the true quotient;
// biasing it down64 then correcting by binary steps yields the exact quotient.
// No approximate quotient is ever returned and no procedural feature is removed.
inline void Rewrite(std::string& source) {
 if(source.find("int retuned_div9(")!=std::string::npos)return;
 if(source.find("int pt_rand1(int v) {")==std::string::npos)return;
 ReplaceOnce(source,"int pt_rand1(int v) {",R"retuned(int retuned_div9(int value) {
 uint n=value<0?0u-uint(value):uint(value);
 uint estimate=uint(float(n)*(1.0/9.0));
 uint q=estimate>64u?estimate-64u:0u;
 uint product=(q<<3u)+q;
 if(n-product>=1152u){q+=128u;product+=1152u;}
 if(n-product>=576u){q+=64u;product+=576u;}
 if(n-product>=288u){q+=32u;product+=288u;}
 if(n-product>=144u){q+=16u;product+=144u;}
 if(n-product>=72u){q+=8u;product+=72u;}
 if(n-product>=36u){q+=4u;product+=36u;}
 if(n-product>=18u){q+=2u;product+=18u;}
 if(n-product>=9u){q+=1u;product+=9u;}
 return value<0?-int(q):int(q);
}
int pt_rand1(int v) {)retuned");
 ReplaceOnce(source,"    return (((v%9+2)*3)&15)^table[(v/9)&15];",R"retuned(    int q=retuned_div9(v);
    uint rem=uint(v)-((uint(q)<<3u)+uint(q));uint a=rem+2u;
    return int((a+(a<<1u))&15u)^table[q&15];)retuned");
 ReplaceOnce(source,"    return (clamp_mode == 3u ? 1.0 : 0.5) * float(((int(coord) + (mode == 2u ? 1 : 0)) / 2) % 2);",R"retuned(    int n=int(coord)+(mode==2u?1:0);uint magnitude=n<0?0u-uint(n):uint(n);
    int parity=int((magnitude>>1u)&1u);if(n<0)parity=-parity;
    return (clamp_mode==3u?1.0:0.5)*float(parity);)retuned");
}
}
