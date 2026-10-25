#include "../tools/frontend/touch_visibility.h"
#include <cassert>
int main() {
 RetunedFrontend::TouchVisibilityState state(false);
 assert(!state.ButtonVisible() && !state.ControlsVisible());
 state.Show(true); // A temporary toggle cannot enable a disabled preference.
 assert(!state.Configured.load() && !state.ButtonVisible() && !state.ControlsVisible());
 state.Configure(true);
 assert(state.ButtonVisible() && state.ControlsVisible());
 state.Show(false); // Keep the eye available without rewriting the setting.
 assert(state.Configured.load() && state.ButtonVisible() && !state.ControlsVisible());
 state.Show(true);
 assert(state.Configured.load() && state.ControlsVisible());
 state.Show(false);
 state.Configure(false);
 assert(!state.ButtonVisible() && !state.ControlsVisible());
 state.Configure(true); // Explicitly enabling controls clears temporary hiding.
 assert(state.ButtonVisible() && state.ControlsVisible());
}
