#include "legacy_hud_anchor.h"
#include <cassert>
int main() {
    std::array<float,33*12> p{};
    for(unsigned i=0;i<p.size();++i)p[i]=float(i);
    const auto original=p;
    for(bool remake:{false,true})for(float hud:{.75f,1.f,1.25f})for(float group:{.5f,.75f,1.f,1.25f}) {
        p=original;
        assert(RetunedRandomizer::AnchorLegacyDpad(p,hud,group,remake));
        assert(std::abs(p[51]-p[48]-10*group*hud)<.001f);
        float left=400;
        for(unsigned q:{4u,8u,9u,10u,11u,12u,23u})left=std::min(left,p[q*12]);
        assert(std::abs(left-8*hud)<.001f);
        auto once=p;assert(RetunedRandomizer::AnchorLegacyDpad(p,hud,group,remake));assert(p==once);
        for(unsigned q=0;q<33;++q) {
            if(q==4||(q>=8&&q<=12)||q==23)continue;
            for(unsigned i=0;i<12;++i)assert(p[q*12+i]==original[q*12+i]);
        }
    }
    auto unchanged=p;
    assert(!RetunedRandomizer::AnchorLegacyDpad(p,1,1.5f));assert(p==unchanged);
}
