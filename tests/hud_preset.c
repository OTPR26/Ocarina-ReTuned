#include "hud_preset.h"
#include "hid.h"
#include <assert.h>

int main(void) {
    const ControlAction actions[] = {CONTROL_ACTION_ITEM_I, CONTROL_ACTION_ITEM_II,
        CONTROL_ACTION_NAVI, CONTROL_ACTION_OCARINA};
    const uint32_t original[] = {BUTTON_LEFT, BUTTON_DOWN, BUTTON_UP, BUTTON_RIGHT};
    const uint32_t remake[] = {BUTTON_UP, BUTTON_DOWN, BUTTON_RIGHT, BUTTON_LEFT};
    assert(HudPreset_Get() == 0);
    for (unsigned preset = 0; preset < 2; ++preset) {
        HudPreset_Set(preset);
        for (unsigned i = 0; i < 4; ++i) {
            const uint32_t button = preset ? remake[i] : original[i];
            assert(HudPreset_Button(actions[i]) == button);
            assert(Controls_Resolve(button, button) == actions[i]);
            assert(Controls_Resolve(button, 0) == actions[i]);
        }
        assert(Controls_Resolve(0, 0) == CONTROL_ACTION_NONE);
        assert(Controls_Resolve(BUTTON_SELECT, BUTTON_SELECT) == CONTROL_ACTION_ITEMS_MENU);
        const uint32_t chord = BUTTON_L1 | BUTTON_R1;
        assert(Controls_Resolve(chord | BUTTON_UP, BUTTON_UP) == CONTROL_ACTION_CAMERA_SENSITIVITY_UP);
        assert(Controls_Resolve(chord | BUTTON_DOWN, BUTTON_DOWN) == CONTROL_ACTION_CAMERA_SENSITIVITY_DOWN);
        assert(Controls_Resolve(chord | BUTTON_LEFT, BUTTON_LEFT) == CONTROL_ACTION_CAMERA_INVERT_PREVIOUS);
        assert(Controls_Resolve(chord | BUTTON_RIGHT, BUTTON_RIGHT) == CONTROL_ACTION_CAMERA_INVERT_NEXT);
        assert(Controls_Resolve(chord, 0) == CONTROL_ACTION_NONE);
    }
    HudPreset_Set(99);assert(HudPreset_Get() == 1);
    HudPreset_Set(0);assert(HudPreset_Button(CONTROL_ACTION_OCARINA) == BUTTON_RIGHT);
}
