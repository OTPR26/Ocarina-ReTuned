"""Install the private, opt-in ReFramed live-presentation experiment.

Not used by release kit staging. Menu-transition and device validation must
finish before enabling this capability in user-facing packages.
"""
from pathlib import Path
import argparse


def apply(root: Path):
    # The native preparer normalizes supported USA inputs to its canonical
    # EUR-addressed image. Match that mod variant, not the input ROM's label.
    if 'Single Screen — EUR' not in (root / 'BUILD.txt').read_text():
        raise ValueError('This experiment requires the canonical native EUR-addressed mod source')
    here = Path(__file__).parent
    for name, directory in (('screen_presentation.h', 'include'),
                            ('screen_presentation.c', 'src')):
        (root / directory / name).write_bytes((here / name).read_bytes())
    path = root / 'src/single_screen.c'
    text = path.read_text()
    marker = '#include "screen_presentation.h"\n'
    if marker in text:
        raise ValueError('Use a fresh isolated mod source for this experiment')
    text = marker + '#include "common.h"\n' + text
    # Each fallback preserves the native call that the wrapper displaced.
    # In particular AfterTopPass must finish the pass before skipping replay.
    guards = {
        'void SingleScreen_BeforeFileScene(void) {': 'return;',
        'void SingleScreen_AfterFileScene(void) {': 'return;',
        'void SingleScreen_DrawFileText(void* context, void (*callback)(void*)) {': 'callback(context); return;',
        'void SingleScreen_BeforeFileBackdrop(void) {': 'return;',
        'static u8 IsGameplayDialogueActive(void) {': 'return 0;',
        'void SingleScreen_DrawDialogueBoards(void* pass) {': '((FinishTopPassFn)ADDR(0x004228B8))(pass); return;',
        'void SingleScreen_DrawDialogueText(void* message) {': '((void (*)(void*))ADDR(0x0042CBA8))(message); return;',
        'void SingleScreen_DrawFileLogoPass(void* pass) {': '((FinishTopPassFn)DRAW_FILE_LOGO_ADDR)(pass); return;',
        'void SingleScreen_DrawSecondaryBackdrop(void* node, void (*draw)(void*)) {': 'draw(node); return;',
        'void SingleScreen_DrawMenuTitle(void* node, void (*draw)(void*)) {': 'draw(node); return;',
        'void SingleScreen_DrawPauseDim(void* context, u32 kind, const float* color, u32 flags) {':
            '((void (*)(void*, u32, const float*, u32))0x003339E8)(context, kind, color, flags); return;',
    }
    for signature, fallback in guards.items():
        if text.count(signature) != 1:
            raise ValueError('Presentation context changed: ' + signature)
        text = text.replace(signature, signature + '\n    if (ScreenPresentation_IsDual()) { ' + fallback + ' }')
    for name in ('BeforeTopOverlay', 'BeforeTopPresentation', 'BeforeMenuTitle',
                 'AfterMenuTitleBoard', 'AfterMenuTitle'):
        signature = 'void SingleScreen_' + name + '(void) {'
        if signature not in text:
            raise ValueError('Missing viewport hook: ' + name)
        # Regional no-op stubs are intentionally left unchanged.
        text = text.replace(signature, signature + '\n    if (ScreenPresentation_IsDual()) return;', 1)
    for before, after in (
        ('    FinishTopPass(pass);\n    if (DrawAuxiliaryUi(pass)) return;',
         '    FinishTopPass(pass);\n    if (ScreenPresentation_IsDual()) return;\n    if (DrawAuxiliaryUi(pass)) return;'),
        ('    ((void (*)(void*))UPDATE_FILE_BOARD_ADDR)(board);',
         '    ((void (*)(void*))UPDATE_FILE_BOARD_ADDR)(board);\n    if (ScreenPresentation_IsDual()) return;'),
    ):
        if text.count(before) != 1:
            raise ValueError('Displaced native call context changed')
        text = text.replace(before, after)
    # Switch only during settled gameplay. File-selection quads and native
    # menu transactions can outlive one draw; never mutate them mid-lifetime.
    text += '''
unsigned ScreenPresentation_CanSwitch(void) {
    extern GlobalContext* gGlobalContext;
    return gGlobalContext != 0 && IsInGameOrBossChallenge() &&
        gSaveContext.gameMode == 0 &&
        *(volatile u8*)(0x005C1878 + 0xF38) == 0 &&
        !InputRemap_IsItemsMenuOpen() && !InputRemap_IsSaveMenuOpen() &&
        !InputRemap_IsOcarinaUiOpen() && !InputRemap_IsGameOverUiOpen() &&
        !UnifiedMenu_GetDialogPage() && !UnifiedMenu_IsOpening() &&
        !UnifiedMenu_IsClosing();
}
'''
    path.write_text(text)
    # Native Dual menus already consume 320x240 input. The unified shell's
    # 400x240 transform would otherwise intercept and misroute those touches.
    inputs = root / 'src/input_remap.c'
    text = marker + inputs.read_text()
    for before, after in (
        ('if (sItemsMenuOpen || sDirectOptions || sPauseOpening || sPauseClosing) {',
         'if (!ScreenPresentation_IsDual() && (sItemsMenuOpen || sDirectOptions || sPauseOpening || sPauseClosing)) {'),
        ('if (sItemsMenuOpen && !sPauseOpening && !sPauseClosing && touchPress) {',
         'if (!ScreenPresentation_IsDual() && sItemsMenuOpen && !sPauseOpening && !sPauseClosing && touchPress) {'),
        ('if (sItemsMenuOpen && !sPauseOpening && !sPauseClosing &&\n        freshTouch && sPhysicalTouchHeld) {',
         'if (!ScreenPresentation_IsDual() && sItemsMenuOpen && !sPauseOpening && !sPauseClosing &&\n        freshTouch && sPhysicalTouchHeld) {'),
        ('if (sItemsMenuOpen && !sFooterFocus && !sFooterNavigationLatch &&',
         'if (!ScreenPresentation_IsDual() && sItemsMenuOpen && !sFooterFocus && !sFooterNavigationLatch &&'),
    ):
        if text.count(before) != 1:
            raise ValueError('Dual menu input context changed')
        text = text.replace(before, after)
    inputs.write_text(text)
    # Keep ReFramed's top-screen HUD in Dual. Its existing visibility settings
    # still control it; a second display is not an implicit Hide HUD request.

    # The native sidebar has a dedicated four-glyph renderer (X, Y, I, II).
    # Suppress only that draw in Dual, as ReMasked does for native item labels.
    # Icon renderers, ammo renderers, fades and touch handling remain native.
    (root / 'src/dual_screen_sidebar.c').write_text((here / 'dual_screen_sidebar.c').read_text())
    patches = root / 'src/patches.s'
    patches.write_text(patches.read_text() + """
.section .patch_DualSidebarSubmission, "ax"
    bl ScreenPresentation_SubmitSidebar
.section .patch_DualGameplayItemLabels, "ax"
    bl ScreenPresentation_DrawItemLabels
.section .patch_DualInventoryItemLabels, "ax"
    bl ScreenPresentation_DrawItemLabels
""")
    linker = root / 'oot_e.ld'
    text = linker.read_text()
    anchor = '\t. = 0x100000;'
    if text.count(anchor) != 1:
        raise ValueError('Canonical sidebar linker context changed')
    linker.write_text(text.replace(anchor, anchor + """
    .patch_DualSidebarSubmission 0x41EAE0 : { *(.patch_DualSidebarSubmission) }
    .patch_DualGameplayItemLabels 0x42F5EC : { *(.patch_DualGameplayItemLabels) }
    .patch_DualInventoryItemLabels 0x434CF0 : { *(.patch_DualInventoryItemLabels) }
"""))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    apply(parser.parse_args().source)
