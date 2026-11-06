#include <assert.h>
static unsigned available = 1, calls, visible = 1;
#define RETUNED_MINIMAP_AVAILABLE() available
#define RETUNED_MINIMAP_TOGGLE() (++calls, visible ^= 1)
#include "../tools/reframed/minimap_toggle.h"

int main(void) {
    const unsigned zl = 1u << 14, zr = 1u << 15;
    unsigned previous = 0;
    const unsigned samples[] = {zr, zr, 0, zl, zl, zl | zr, zr, 0, zl | zr};
    for (unsigned i = 0; i < sizeof(samples)/sizeof(samples[0]); ++i) {
        RetunedMinimap_Update(samples[i] & ~previous, 1);
        previous = samples[i];
        assert(calls == (i < 3 ? 0u : i < 8 ? 1u : 2u));
    }
    assert(visible == 1);
    available = 0;
    RetunedMinimap_Update(zl, 1);
    assert(calls == 2);
    available = 1;
    RetunedMinimap_Update(zl, 0);
    assert(calls == 2);
    /* Native state can change independently, including across scene loads. */
    visible = 0;
    RetunedMinimap_Update(zl, 1);
    assert(calls == 3 && visible == 1);
    return 0;
}
