"""Stage independent gameplay HUD group sizes."""
from pathlib import Path


def apply(root: Path):
    from apply_hud_preset import replace_once
    p = Path(root) / 'src/native_hud.c'
    text = p.read_text()
    text = text.replace("percent > (group == 0 ? 150 : 125) || percent % 25",
                        "percent > 125 || percent % 25")
    marker = 'static void NativeHud_RebuildPositions(void) {'
    helper = '''static u32 sNativeHudGroupScale[2] = {100, 100};
static float NativeHud_GroupScale(u32 group) {
    if (sNativeHudDualMenuLayout || (sNativeHudOcarinaLayout && group == 1)) return 1.0f;
    return sNativeHudGroupScale[group] / 100.0f;
}
static void NativeHud_ScaleGroups(void) {
    if (sNativeHudDualMenuLayout) return;
    const float dpad = NativeHud_GroupScale(0);
    const u32 dpadQuads[] = {4, 8, 9, 10, 11, 23, 12};
    const u32 count = sNativeHudOcarinaLayout ? 6 : 7;
    float left = gNativeHudPositions[4 * 12];
    for (u32 i = 0; i < count; ++i)
        for (u32 v = 0; v < 4; ++v) {
            const float x = gNativeHudPositions[dpadQuads[i] * 12 + v * 3];
            if (x < left) left = x;
        }
    for (u32 i = 0; i < count; ++i) {
        NativeHud_ScaleQuad(dpadQuads[i], left, 67.5f, dpad);
        NativeHud_TranslateQuad(dpadQuads[i], 8.0f - left, 0.0f);
    }
    if (sNativeHudOcarinaLayout) return;
    const float actions = NativeHud_GroupScale(1);
    NativeHud_ScaleQuadRange(1, 3, 400.0f, 0.0f, actions);
    NativeHud_ScaleQuadRange(5, 7, 400.0f, 0.0f, actions);
    NativeHud_ScaleQuadRange(28, 29, 400.0f, 0.0f, actions);
    NativeHud_ScaleQuadRange(33, 96, 400.0f, 0.0f, actions);
}
'''
    if 'static u32 sNativeHudGroupScale' in text:
        start = text.index('static u32 sNativeHudGroupScale')
        end = text.index(marker, start)
        text = text[:start] + helper + text[end:]
    else:
        text = replace_once(text, marker, helper + marker)
    marker = '    if (sNativeHudScalePercent == 100) {'
    text = replace_once(text, marker, '    NativeHud_ScaleGroups();\n' + marker)
    marker = 'static u32 NativeHud_UvHash(void) {'
    exports = '''u32 NativeHud_GetGroupScale(u32 group) {
    return group < 2 ? sNativeHudGroupScale[group] : 100;
}
void NativeHud_SetGroupScale(u32 group, u32 percent) {
    if (group >= 2 || percent < 50 || percent > 125 || percent % 25) return;
    if (sNativeHudGroupScale[group] == percent) return;
    sNativeHudGroupScale[group] = percent;
    NativeHud_RebuildPositions();
}

'''
    text = replace_once(text, marker, exports + marker)
    text = replace_once(text, '        const float hudScale = NativeHud_GetScale();',
                        '        const float hudScale = NativeHud_GetScale() * NativeHud_GroupScale(1);')
    text = text.replace('if (!sNativeHudDualMenuLayout && !sNativeHudOcarinaLayout) {\n        // Restoration-sized gameplay cluster; retain the menu diagrams.',
                        'if (!sNativeHudDualMenuLayout) {\n        // Restoration-sized gameplay cluster; retain the menu diagrams.')
    text = text.replace('        NativeHud_ScaleQuadRange(8, 12, 40.0f, 78.5f, 0.65f);',
                        '        NativeHud_ScaleQuadRange(8, 11, 40.0f, 78.5f, 0.65f);\n        if (!sNativeHudOcarinaLayout) NativeHud_ScaleQuad(12, 40.0f, 78.5f, 0.65f);')
    text = text.replace('        for (u32 quad=8; quad<=12; ++quad) NativeHud_TranslateQuad(quad, 0.0f, -11.0f);',
                        '        for (u32 quad=8; quad<=11; ++quad) NativeHud_TranslateQuad(quad, 0.0f, -11.0f);\n        if (!sNativeHudOcarinaLayout) NativeHud_TranslateQuad(12, 0.0f, -11.0f);')
    p.write_text(text)
