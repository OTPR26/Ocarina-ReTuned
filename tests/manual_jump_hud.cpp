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
    for(const auto& p:ManualJump_BumperPatches) {
        assert(!CoversCenter(p,0,1,2)&&!CoversCenter(p,1,2,3));
        for(int v=0;v<4;++v) {
            assert(std::isfinite(p[v*2])&&std::isfinite(p[v*2+1]));
            assert(p[v*2]>=369.99f&&p[v*2]<=392.01f);
            assert(p[v*2+1]>=14.99f&&p[v*2+1]<=25.01f);
        }
    }
    // Each ring patch joins the next, including the wraparound. Both sides
    // of the strip use the same point order to avoid folded triangles.
    for(int i=0;i<64;++i) {
        const auto& p=ManualJump_BumperPatches[i];
        const auto& next=ManualJump_BumperPatches[(i+1)%64];
        assert(p[2]==next[0]&&p[3]==next[1]);
        assert(p[6]==next[4]&&p[7]==next[5]);
    }
}
