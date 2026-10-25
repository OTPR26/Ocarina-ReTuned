#include <assert.h>
#include "screen_presentation.h"
static unsigned ready;
unsigned ScreenPresentation_CanSwitch(void) { return ready; }
int main(void) {
    assert(ScreenPresentation_GetMode() == 0);
    assert(ScreenPresentation_TrySetMode(0));
    assert(!ScreenPresentation_TrySetMode(1));
    assert(!ScreenPresentation_IsDual());
    ready = 1;
    assert(ScreenPresentation_TrySetMode(1));
    assert(ScreenPresentation_IsDual());
    assert(!ScreenPresentation_TrySetMode(2));
    assert(!ScreenPresentation_TrySetMode(~0u));
    assert(ScreenPresentation_IsDual());
    ready = 0;
    assert(ScreenPresentation_TrySetMode(1));
    assert(!ScreenPresentation_TrySetMode(0));
    assert(ScreenPresentation_IsDual());
    ready = 1;
    assert(ScreenPresentation_TrySetMode(0));
    assert(!ScreenPresentation_IsDual());
}
