"""Adapt a local Reframed source copy to the native app's pause-menu footer."""
from pathlib import Path
import argparse
from apply_native_port import edit

def apply(root):
    menu=root/'src/unified_menu.c'
    edit(menu,'            const bool options = q>=18 && q<=21;','            const bool options = false;')
    edit(menu,'    if (!focus || focus>2) return;','    if (!focus || focus>1) return;')
    edit(menu,'static void DrawFooter(void) {','static void DrawFooter(void) {\n    __asm__ volatile("svc #0x7d" ::: "r0", "memory", "cc");')
    touch=root/'include/menu_touch.h'
    edit(touch,'    if (MenuTouch_In(x,y,285,209,70,20)) return 2;','    /* Tab hints occupy the former Options area; it is not a button. */')
    inputs=root/'src/input_remap.c'
    (root/'include/retuned_pause_close.h').write_text(
        (Path(__file__).parents[1]/'frontend/pause_close.h').read_text())
    edit(inputs,'#include "unified_menu_navigation.h"',
         '#include "unified_menu_navigation.h"\n#include "retuned_pause_close.h"')
    edit(inputs,'sFooterOpenOptions = sFooterFocus == 2;', 'sFooterOpenOptions = 0;')
    edit(inputs,'    if (sPauseClosing) {',
         '    if (sPauseClosing) {\n        const unsigned stillOpen=RetunedPausePageStillOpen(mode);\n        if (stillOpen) {\n            sPauseClosing = sPauseCloseSettled = 0;\n            sItemsMenuOpen = 1;\n            sActivePausePage = stillOpen;\n            return;\n        }')

    edit(inputs,'if (pressed & (BUTTON_RIGHT | CPAD_RIGHT)) sFooterFocus = 2;','if (pressed & (BUTTON_RIGHT | CPAD_RIGHT)) sFooterFocus = 1;')
    edit(inputs,'            sFooterFocus = dialogKind == 1 ? 2 : 1;','            sFooterFocus = 1;')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);apply(parser.parse_args().source)
