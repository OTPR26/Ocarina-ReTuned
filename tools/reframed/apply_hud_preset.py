"""Add the opt-in Remake mapping to the canonical native game bridge."""
from pathlib import Path


def replace_once(text, old, new):
    if new in text:
        return text
    if text.count(old) != 1:
        raise ValueError('HUD preset source context changed: ' + old[:90])
    return text.replace(old, new)


def apply(root: Path):
    root = Path(root)
    if 'Single Screen — EUR' not in (root / 'BUILD.txt').read_text():
        raise ValueError('HUD presets require the canonical native EUR-addressed source')
    makefile = root / 'Makefile'
    if makefile.exists():
        makefile.write_text(replace_once(makefile.read_text(),
            'tests/controls_test.c src/controls.c src/controller_settings.c',
            'tests/controls_test.c src/controls.c src/hud_preset.c src/controller_settings.c'))
    here = Path(__file__).parent
    for name, directory in [('hud_preset.h', 'include'), ('hud_preset.c', 'src')]:
        (root / directory / name).write_bytes((here / name).read_bytes())
    for filename in ['controls.c', 'input_remap.c', 'native_hud.c']:
        p = root / 'src' / filename
        text = p.read_text()
        if '#include "hud_preset.h"' not in text:
            text = '#include "hud_preset.h"\n' + text
        if filename == 'controls.c':
            for direction, action in [('LEFT', 'ITEM_I'), ('DOWN', 'ITEM_II'), ('UP', 'NAVI'), ('RIGHT', 'OCARINA')]:
                old = f'if (held & BUTTON_{direction}) {{\n        return CONTROL_ACTION_{action};'
                new = f'if (held & HudPreset_Button(CONTROL_ACTION_{action})) {{\n        return CONTROL_ACTION_{action};'
                text = replace_once(text, old, new)
        elif filename == 'input_remap.c':
            pairs = [
                ('dpadButton == BUTTON_LEFT ? 5 : 0x17', 'dpadButton == HudPreset_Button(CONTROL_ACTION_ITEM_I) ? 5 : 0x17'),
                ('pauseDpadPressed == BUTTON_LEFT || pauseDpadPressed == BUTTON_DOWN',
                 'pauseDpadPressed == HudPreset_Button(CONTROL_ACTION_ITEM_I) || pauseDpadPressed == HudPreset_Button(CONTROL_ACTION_ITEM_II)'),
                ('pauseDpadPressed == BUTTON_LEFT ? BUTTON_X : BUTTON_Y',
                 'pauseDpadPressed == HudPreset_Button(CONTROL_ACTION_ITEM_I) ? BUTTON_X : BUTTON_Y'),
                ('action == CONTROL_ACTION_ITEM_I ? BUTTON_LEFT : BUTTON_DOWN', 'HudPreset_Button(action)'),
                ('if (rInputCtx.pressed.val & BUTTON_RIGHT) {', 'if (rInputCtx.pressed.val & HudPreset_Button(CONTROL_ACTION_OCARINA)) {'),
            ]
            for old, new in pairs:
                text = replace_once(text, old, new)
            boundary = "\n}\n\nu32 InputRemap_TryOpenItemsMenu(void* menuManager) {"
            mapping = """
    /* Remap only final gameplay input, after native menu navigation. */
    const int remakeGameplay = globalCtx && gSaveContext.gameMode == 0 &&
        gSaveContext.health && *(volatile u32*)0x0050AF68 == 2 &&
        !sItemsMenuRequested && !InputRemap_IsItemsMenuOpen() &&
        !InputRemap_IsSaveMenuOpen() && !InputRemap_IsOcarinaUiOpen() &&
        !InputRemap_IsGameOverUiOpen();
#define REMAKE_MASK(value) value = HudPreset_GameplayMask(value, remakeGameplay)
    REMAKE_MASK(hidPad->curr.val); REMAKE_MASK(hidPad->pressed.val);
    REMAKE_MASK(hidPad->released.val);
    REMAKE_MASK(*gameHeld); REMAKE_MASK(*gamePressed); REMAKE_MASK(*gameReleased);
    REMAKE_MASK(rInputCtx.cur.val); REMAKE_MASK(rInputCtx.pressed.val);
    REMAKE_MASK(rInputCtx.up.val);
#undef REMAKE_MASK
"""
            text = replace_once(text, boundary, mapping + boundary)

        else:
            if 'static void NativeHud_PositionPreset(void)' not in text:
                text = replace_once(text, 'static void NativeHud_RebuildPositions(void) {', '''static u32 sHudPresetApplied;
    static void NativeHud_PositionPreset(void) {
        if (HudPreset_Get() != 1) return;
        NativeHud_TranslateQuad(8, -34.0f, 0.0f); /* Ocarina: left */
        NativeHud_TranslateQuad(9, 17.0f, 20.0f); /* Navi: right */
        NativeHud_TranslateQuad(10, 17.0f, -20.0f); /* Item I: up */
        NativeHud_TranslateQuad(12, 17.0f, -20.0f); /* Item I ammo */
    }
    static void NativeHud_RebuildPositions(void) {''')
            text = replace_once(text, '        gNativeHudPositions[i] = sNativeHudBasePositions[i];\n    }',
                                '        gNativeHudPositions[i] = sNativeHudBasePositions[i];\n    }\n    NativeHud_PositionPreset();')
            text = replace_once(text, '    const u8 dual = ScreenPresentation_IsDual();', '''    const u8 dual = ScreenPresentation_IsDual();
    if (sHudPresetApplied != HudPreset_Get()) {
        sHudPresetApplied = HudPreset_Get();
        NativeHud_RebuildPositions();
    }''')
            if '// Restoration-sized gameplay cluster; retain the menu diagrams.' not in text:
                text = replace_once(text, '    if (sNativeHudScalePercent == 100) {', '''    if (!sNativeHudDualMenuLayout && !sNativeHudOcarinaLayout) {
        // Restoration-sized gameplay cluster; retain the menu diagrams.
        NativeHud_ScaleQuad(4, 40.0f, 78.5f, 0.5f);
        NativeHud_ScaleQuadRange(8, 12, 40.0f, 78.5f, 0.65f);
        NativeHud_ScaleQuad(23, 40.0f, 78.5f, 0.65f);
    }
    if (sNativeHudScalePercent == 100) {''')
        if filename == 'native_hud.c':
            text = replace_once(text,
                '    NativeHud_TranslateQuad(12, 17.0f, -20.0f); /* Item I ammo */',
                '''    NativeHud_TranslateQuad(12, 17.0f, -20.0f); /* Item I ammo */
    if (!sNativeHudDualMenuLayout && !sNativeHudOcarinaLayout) {
        NativeHud_TranslateQuad(5, -17.0f, -17.0f); /* Sword: west */
        NativeHud_TranslateQuad(7, 17.0f, 17.0f); /* Y item: south */
        NativeHud_TranslateQuad(29, 17.0f, 17.0f); /* Y item ammo */
    }''')
            if '(p[1]+p[7])*0.5f, 1.1f);' not in text:
                text = replace_once(text,
                    '        NativeHud_ScaleQuadRange(8, 12, 40.0f, 78.5f, 0.65f);',
                    '''        for (u32 quad=8; quad<=11; ++quad) {
                const float* p = gNativeHudPositions + quad * 12;
                NativeHud_ScaleQuad(quad, (p[0]+p[3])*0.5f,
                                    (p[1]+p[7])*0.5f, 1.1f);
            }
            NativeHud_ScaleQuadRange(8, 12, 40.0f, 78.5f, 0.65f);''')
            if 'NativeHud_TranslateQuad(4, 0.0f, -11.0f);' not in text:
                text = replace_once(text,
                    '        NativeHud_ScaleQuad(23, 40.0f, 78.5f, 0.65f);',
                    '        NativeHud_ScaleQuad(23, 40.0f, 78.5f, 0.65f);\n'
                    '        NativeHud_TranslateQuad(4, 0.0f, -11.0f);\n'
                    '        for (u32 quad=8; quad<=12; ++quad) NativeHud_TranslateQuad(quad, 0.0f, -11.0f);\n'
                    '        NativeHud_TranslateQuad(23, 0.0f, -11.0f);')
        p.write_text(text)

    from apply_hud_sizes import apply as apply_hud_sizes
    apply_hud_sizes(root)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    apply(parser.parse_args().source)
