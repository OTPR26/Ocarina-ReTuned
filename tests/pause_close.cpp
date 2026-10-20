#include "pause_close.h"
#include <cassert>
#include <initializer_list>
int main() {
    // A close consumed by an item-selection action must retain its visible page.
    assert(RetunedPausePageStillOpen(0x0c)==1);
    assert(RetunedPausePageStillOpen(0x10)==2);
    assert(RetunedPausePageStillOpen(0x14)==3);
    // Acknowledged close transitions and gameplay must not resurrect a page.
    for(unsigned mode: {0u,2u,7u,0x0du,0x11u,0x15u})
        assert(RetunedPausePageStillOpen(mode)==0);
}
