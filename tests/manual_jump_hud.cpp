#include "../tools/reframed/manual_jump_hud.h"
#include <cassert>
#include <cmath>
static bool CoversCenter(const float* p,int a,int b,int c) {
    const float x=381,y=20;
    auto side=[&](int i,int j){return (p[j*2]-p[i*2])*(y-p[i*2+1])-(p[j*2+1]-p[i*2+1])*(x-p[i*2]);};
    const float ab=side(a,b),bc=side(b,c),ca=side(c,a);
    return (ab>0.0001f&&bc>0.0001f&&ca>0.0001f)||(ab<-.0001f&&bc<-.0001f&&ca<-.0001f);
}
int main() {
    constexpr int mirrorOrder[]{1,0,3,2};
    for(int q=0;q<64;++q)for(int v=0;v<4;++v) {
        const int r=mirrorOrder[v];
        assert(std::abs(ManualJump_LeftBumperPatches[q][v*2]+
                        ManualJump_BumperPatches[q][r*2]-762.f)<.0001f);
        assert(ManualJump_LeftBumperPatches[q][v*2+1]==ManualJump_BumperPatches[q][r*2+1]);
        for(int axis=0;axis<2;++axis)
            assert(ManualJump_LeftBumperUVs[q][v*2+axis]==ManualJump_BumperUVs[q][r*2+axis]);
    }

    for(const auto& p:ManualJump_BumperPatches) {
        assert(!CoversCenter(p,0,1,2)&&!CoversCenter(p,1,2,3));
        for(int v=0;v<4;++v) {
            assert(std::isfinite(p[v*2])&&std::isfinite(p[v*2+1]));
            assert(p[v*2]>=369.99f&&p[v*2]<=392.01f);
            assert(p[v*2+1]>=14.99f&&p[v*2+1]<=25.01f);
        }
    }
    // Adjacent wedges share both geometry and texture coordinates.
    for(int i=0;i<64;++i) {
        const auto& p=ManualJump_BumperPatches[i];
        const auto& next=ManualJump_BumperPatches[(i/32)*32+(i+1)%32];
        assert(p[2]==next[0]&&p[3]==next[1]);
        assert(p[6]==next[4]&&p[7]==next[5]);
        if(i>=32)assert(p[4]==381.f&&p[5]==20.f&&p[6]==381.f&&p[7]==20.f);
        const auto& uv=ManualJump_BumperUVs[i];
        const auto& nextUV=ManualJump_BumperUVs[(i/32)*32+(i+1)%32];
        assert(uv[2]==nextUV[0]&&uv[3]==nextUV[1]);
        for(int v=0;v<4;++v){
            assert(uv[2*v]>=48.f/512.f && uv[2*v]<=85.f/512.f);
            assert(uv[2*v+1]>=218.f/256.f && uv[2*v+1]<=1.f);
        }
        if(i>=32)assert(std::abs(uv[4]-66.5f/512.f)<1e-6f);
        if(i>=32) {
            assert(std::abs(uv[5]-(1.f-19.f/256.f))<1e-6f);
            // Glass intensity depends on height only, not distance to a corner.
            for(int v=0;v<4;++v)assert(std::abs(uv[v*2]-66.5f/512.f)<1e-6f);
        }
    }
}
