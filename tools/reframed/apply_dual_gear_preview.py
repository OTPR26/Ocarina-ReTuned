"""Balance Dual Gear spacing and share its description sizing with Items."""
from pathlib import Path


def apply(root: Path):
    root = Path(root)
    path = root / 'src/gear_preview.c'
    text = path.read_text().replace('(4,60,336,280);', '(22,60,336,280);')
    marker = '#include "screen_presentation.h"\n'
    before = """    ((void (*)(unsigned,int,unsigned,unsigned))0x002FEABC)
        (48,-30-MENU_GEAR_PORTRAIT_SHIFT,336,252);"""
    after = """    /* Dual has the full top screen for its preview. Center the portrait
     * above a smaller help board; Single keeps its right lane. */
    if (ScreenPresentation_IsDual())
        ((void (*)(unsigned,int,unsigned,unsigned))0x002FEABC)(16,62,368,276);
    else {
""" + before + """
    }"""
    restore = '    ((void (*)(unsigned,int,unsigned,unsigned))0x002FEABC)(88,6,240,180);'
    if marker not in text:
        if text.count(before) != 1 or text.count(restore) != 1:
            raise ValueError('Gear preview viewport context changed')
        text = marker + text.replace(before, after).replace(restore, """    if (ScreenPresentation_IsDual())
        ((void (*)(unsigned,int,unsigned,unsigned))0x002FEABC)(0,60,336,280);
    else {
""" + restore + """
    }""")
    # Rotated GPU X moves the board vertically. Twenty-two units place the board between
    # the floating doll’s feet and the screen edge (not the live actor behind it).
    text = text.replace('(0,60,336,280);', '(22,60,336,280);')
    item = '''    /* Dual Items retains its full-size native rotating item. Only the
     * description uses the compact Gear help transform. */
    if (ScreenPresentation_IsDual() && InputRemap_IsItemsPageActive() &&
        !UnifiedMenu_IsOpening() && !UnifiedMenu_IsClosing() && !UnifiedMenu_GetDialogPage()) {
        ((void (*)(unsigned,int,unsigned,unsigned))0x002FEABC)(0,0,480,400);
        nativeDraw(queue);
        ((void (*)(unsigned,int,unsigned,unsigned))0x002FEABC)(22,60,336,280);
        return;
    }
'''
    previous_item = item.replace(
        'Dual Items retains its full-size native rotating item. Only the\n     * description uses the compact Gear help transform.',
        'Dual Items uses the same preview viewport as Gear. Keep the\n     * native rotating item and restore the shared help transform after it.'
    ).replace('(0,0,480,400);', '(16,62,368,276);')
    text = text.replace(previous_item, '')
    if item not in text:
        anchor = '    void (*nativeDraw)(void*) = (void (*)(void*))ADDR(0x004224E8);\n'
        if text.count(anchor) != 1:
            raise ValueError('Items preview draw context changed')
        text = text.replace(anchor, anchor + item)
    transition = '    if (ScreenPresentation_IsDual() && UnifiedMenu_IsClosing()) return;\n'
    if transition not in text:
        text = text.replace('    void (*nativeDraw)(void*) = (void (*)(void*))ADDR(0x004224E8);\n',
                            '    void (*nativeDraw)(void*) = (void (*)(void*))ADDR(0x004224E8);\n' + transition)
    path.write_text(text)
    path = root / 'src/single_screen.c'
    text = path.read_text().replace('(4,60,336,280);', '(22,60,336,280);')
    # Upgrade the first comparison: never scale the whole top-HUD group.
    previous = """void SingleScreen_BeforeTopPresentation(void) {
    if (ScreenPresentation_IsDual()) {
        if (InputRemap_IsItemsMenuOpen() &&
            (InputRemap_IsItemsPageActive() || InputRemap_IsGearPageActive()) &&
            !UnifiedMenu_IsOpening() && !UnifiedMenu_IsClosing() && !UnifiedMenu_GetDialogPage())
            SetViewport(22,60,336,280);
        return;
    }"""
    text = text.replace(previous, 'void SingleScreen_BeforeTopPresentation(void) {\n    if (ScreenPresentation_IsDual()) return;')
    for name in ('BeforeTopOverlay',):
        before = 'void SingleScreen_' + name + '(void) {\n    if (ScreenPresentation_IsDual()) return;'
        after = 'void SingleScreen_' + name + '''(void) {
    if (ScreenPresentation_IsDual()) {
        if (InputRemap_IsItemsMenuOpen() &&
            (InputRemap_IsItemsPageActive() || InputRemap_IsGearPageActive()) &&
            !UnifiedMenu_IsOpening() && !UnifiedMenu_IsClosing() && !UnifiedMenu_GetDialogPage())
            SetViewport(22,60,336,280);
        return;
    }'''
        scoped_close = 'void SingleScreen_' + name + '(void) {\n    if (ScreenPresentation_IsDual()) {\n        if (UnifiedMenu_IsClosing()) {'
        if after not in text and scoped_close not in text:
            if text.count(before) != 1:
                raise ValueError('Dual description viewport context changed: ' + name)
            text = text.replace(before, after)
    if 'static unsigned char sDualPreviewClosingClip;' not in text:
        text = text.replace('#include "screen_presentation.h"\n',
                            '#include "screen_presentation.h"\nstatic unsigned char sDualPreviewClosingClip;\n', 1)
    closing_overlay = """    if (ScreenPresentation_IsDual()) {
        if (UnifiedMenu_IsClosing()) {
            // Hide stale native item/help geometry through the final close frame.
            SetScissor(1,0,0,479,399);
            sDualPreviewClosingClip = 1;
            return;
        }
        if (InputRemap_IsItemsMenuOpen() &&"""
    if closing_overlay not in text:
        begin = text.index('void SingleScreen_BeforeTopOverlay(void) {')
        part = text[begin:]
        old = '    if (ScreenPresentation_IsDual()) {\n        if (InputRemap_IsItemsMenuOpen() &&'
        if part.count(old) != 1:
            raise ValueError('Dual closing overlay scope changed')
        text = text[:begin] + part.replace(old,closing_overlay,1)
    old_finish = '    FinishTopPass(pass);\n    if (ScreenPresentation_IsDual()) return;'
    new_finish = """    FinishTopPass(pass);
    if (ScreenPresentation_IsDual()) {
        if (sDualPreviewClosingClip) {
            SetScissor(0,0,0,479,399);
            sDualPreviewClosingClip = 0;
        }
        return;
    }"""
    if new_finish not in text:
        if text.count(old_finish) != 1:
            raise ValueError('Dual closing clip restoration scope changed')
        text = text.replace(old_finish,new_finish)
    path.write_text(text)
