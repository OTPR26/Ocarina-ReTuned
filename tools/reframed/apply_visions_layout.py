"""Arrange the native Visions browser in Single mode without moving Dual UI."""
from pathlib import Path


def apply(root: Path):
    path = Path(root) / 'src/single_screen.c'
    source = path.read_text()
    replacements = (
        ('''        // Native upper image: 200 x 120, centered in the left half.
        SetViewport(120, 200, 240, 200);
        callback(context);''',
         '''        const u32 hintState = *(u32*)((u8*)context + 0x104);
        if (hintState >= 2) {
            // Movie startup, playback, and return fades own the full screen.
            SetViewport(0, 0, 480, 400);
            callback(context);
        } else {
            // The native upper callback owns the description background and
            // text. Keep both in one preparation/draw at the same viewport.
            SetViewport(190, 0, 260, 200);
            callback(context);
            SetViewport(0, 0, 480, 400);
        }'''),
        ('    if (hint) {\n#if defined(Version_USA)',
         '''    if (hint) {
        if (*(u32*)((u8*)hint + 0x104) >= 2) {
            // Do not replay the lower browser over full-screen playback.
            SetViewport(0, 0, 480, 400);
            return 1;
        }
#if defined(Version_USA)'''),
        ('// Lower Visions list and queued controls, beside the native video.\n        SetViewport(90, 0, 300, 200);',
         '// Location and vision choices share the left-hand column.\n        SetViewport(90, 200, 300, 200);'),
        ('        ((DrawSecondaryCallbackFn)ADDR(0x00477E10))(hint);\n        ((FinishTopPassFn)DRAW_TITLE_ADDR)(pass);',
         '''        ((DrawSecondaryCallbackFn)ADDR(0x00477E10))(hint);
        DrawHintBrowserControls(pass);'''),
        ('static u8 DrawAuxiliaryUi(void* pass) {',
         '''static void DrawHintBrowserControls(void* pass) {
    if (!pass) return;
    u32* count = (u32*)((u8*)pass + 0x2c);
    void** nodes = (void**)((u8*)pass + 0x454);
    const u32 originalCount = *count;
    void* saved[24];
    u8 category[24];
    if (originalCount > 24) {
        SetViewport(90, 200, 300, 200);
        ((FinishTopPassFn)DRAW_TITLE_ADDR)(pass);
        return;
    }
    for (u32 i = 0; i < originalCount; ++i) {
        saved[i] = nodes[i];
        // Back and the prompt need separate viewports.
        category[i] = 0;
        if (saved[i] && ((u32*)saved[i])[0] == BOARD_VTABLE_ADDR)
            category[i] = ((float*)saved[i])[16] >= 180.0f ? 1 : 2;
    }
    for (u32 group = 0; group < 3; ++group) {
        u32 n = 0;
        for (u32 i = 0; i < originalCount; ++i)
            if (saved[i] && category[i] == group) nodes[n++] = saved[i];
        *count = n;
        if (!n) continue;
        if (group == 1)
            SetViewport(0, 200, 300, 200); // Back
        else
            SetViewport(180, 120, 240, 160); // prompt
        ((FinishTopPassFn)DRAW_TITLE_ADDR)(pass);
    }
    for (u32 i = 0; i < originalCount; ++i) nodes[i] = saved[i];
    *count = originalCount;
}

static u8 DrawAuxiliaryUi(void* pass) {'''),
    )
    for before, after in replacements:
        if after in source:
            continue
        if source.count(before) != 1:
            raise ValueError('Visions presentation context changed: ' + before)
        source = source.replace(before, after)
    if 'void SingleScreen_AdjustHintTitle(float* bounds)' not in source:
        source += """
void SingleScreen_AdjustHintTitle(float* bounds) {
    if (ScreenPresentation_IsDual() || !bounds) return;
    // Native order is top, bottom, left, right; preserve center and UVs.
    if (bounds[0] != 8.0f || bounds[1] != 40.0f ||
        bounds[2] != 112.0f || bounds[3] != 288.0f) return;
    bounds[0] = 16.0f; bounds[1] = 32.0f;
    bounds[2] = 156.0f; bounds[3] = 244.0f;
}
"""
    path.write_text(source)
    additions = {
        'src/hooks.s': """\n.if (_USA_==1) || (_EUR_==1)
.text
.global hook_VisionsTitleBounds
hook_VisionsTitleBounds:
    push {r0-r12, lr}
    vpush {d0-d7}
    mov r0, r3
    bl SingleScreen_AdjustHintTitle
    vpop {d0-d7}
    pop {r0-r12, lr}
    b 0x002D04C0
.endif
""",
        'src/patches.s': """\n.if (_USA_==1) || (_EUR_==1)
.section .patch_VisionsTitleBounds, "ax"
    bl hook_VisionsTitleBounds
.endif
""",
    }
    for name, addition in additions.items():
        target = Path(root) / name
        text = target.read_text()
        if 'hook_VisionsTitleBounds' not in text:
            target.write_text(text + addition)
    for name, address in [('oot.ld', '0x470AB4'), ('oot_e.ld', '0x470AD4')]:
        target = Path(root) / name
        text = target.read_text()
        if '.patch_VisionsTitleBounds' not in text:
            if text.count('SECTIONS\n{') != 1:
                raise ValueError('Visions linker context changed: ' + name)
            text = text.replace('SECTIONS\n{', 'SECTIONS\n{\n    .patch_VisionsTitleBounds ' + address + ' : { *(.patch_VisionsTitleBounds) }', 1)
            target.write_text(text)
