#pragma once
#include <array>
#include <cmath>
#include <span>
#include <algorithm>

namespace RetunedRandomizer {
// Compatibility for retained images without NativeHud_SetGroupScale. Rebuild
// from native coordinates so repeated uploads cannot accumulate scaling.
inline bool AnchorLegacyDpad(std::span<float> positions, float hudScale=1.f,
                             float groupScale=1.f, bool remake=true) {
    if(positions.size()<24*12 || !std::isfinite(hudScale) ||
       !std::isfinite(groupScale) || hudScale<0 || hudScale>1.25f ||
       groupScale<.5f || groupScale>1.25f)return false;
    constexpr std::array<unsigned,7> quads{4,8,9,10,11,12,23};
    std::array<std::array<float,4>,7> rects{{
        {30,89,50,68},{50,85,64,71},{34,64,46,52},
        {16,85,30,71},{33,105,47,91},{23,85,30,80},{40,105,47,100}}};
    if(remake) {
        for(auto i:{1,2,3,5}) {
            const float dx=i==1?-34.f:17.f,dy=i==1?0.f:i==2?20.f:-20.f;
            rects[i][0]+=dx;rects[i][2]+=dx;rects[i][1]+=dy;rects[i][3]+=dy;
        }
    }
    float left=400.f;
    for(unsigned i=0;i<rects.size();++i) {
        auto& r=rects[i];
        if(i>=1&&i<=4) {
            const float x=(r[0]+r[2])*.5f,y=(r[1]+r[3])*.5f;
            r={x+(r[0]-x)*1.1f,y+(r[1]-y)*1.1f,
               x+(r[2]-x)*1.1f,y+(r[3]-y)*1.1f};
        }
        const float scale=i==0?.5f:.65f;
        r={40+(r[0]-40)*scale,78.5f+(r[1]-78.5f)*scale-11,
           40+(r[2]-40)*scale,78.5f+(r[3]-78.5f)*scale-11};
        left=std::min(left,r[0]);
    }
    for(unsigned i=0;i<rects.size();++i)for(unsigned v=0;v<4;++v) {
        auto& p=positions[quads[i]*12+v*3];
        p=(8+(rects[i][v%2?2:0]-left)*groupScale)*hudScale;
        positions[quads[i]*12+v*3+1]=(67.5f+(rects[i][v<2?1:3]-67.5f)*groupScale)*hudScale;
    }
    return true;
}
}
