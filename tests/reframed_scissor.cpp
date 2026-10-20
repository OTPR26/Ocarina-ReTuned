#include "../tools/reframed/exclude_scissor.h"
#include <cassert>
using Retuned::ScissorRect;
bool contains(ScissorRect r, int x, int y) {
    return x >= r.X && y >= r.Y && int64_t{x} < int64_t{r.X}+r.Width && int64_t{y} < int64_t{r.Y}+r.Height;
}
int main() {
    // Check exact coverage and absence of overlapping fragments for clipped,
    // empty, covering, edge-touching and partially out-of-bounds rectangles.
    for (int hx=-3; hx<12; ++hx) for (int hy=-3; hy<10; ++hy)
    for (unsigned hw=0; hw<14; ++hw) for (unsigned hh=0; hh<12; ++hh) {
        ScissorRect bounds{1,2,8,6}, hole{hx,hy,hw,hh};
        auto parts=Retuned::ExcludeScissor(bounds,hole);
        assert(parts.Count<=4);
        for (int x=-4; x<15; ++x) for(int y=-4; y<15; ++y) {
            int count=0;
            for(unsigned i=0;i<parts.Count;++i) count+=contains(parts.Rects[i],x,y);
            assert(count==int(contains(bounds,x,y) && !contains(hole,x,y)));
        }
    }
    auto large=Retuned::ExcludeScissor({0,0,0xFFFFFFFFU,0xFFFFFFFFU},{0,0,0xFFFFFFFFU,0xFFFFFFFFU});
    assert(large.Count==0);
}
