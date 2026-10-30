"""Keep localized fade-only passes in the full-screen viewport."""
from pathlib import Path
from apply_native_port import edit


def apply(root):
    anchor = '    SetViewport(sFileGuidanceVisible ? 290 : 392, 114, 324, 324);\n    if (splitFade) {'
    guard = '''    const u8 fadeOnly = *count == 1 && nodes[0] != 0 &&
        nodes[0][0] == BOARD_VTABLE_ADDR &&
        ((float*)nodes[0])[15] == 200.0f &&
        ((float*)nodes[0])[16] == 120.0f;
    if (fadeOnly) {
        SetViewport(0, 0, 480, 400);
        drawPass(pass);
        return;
    }

'''
    edit(Path(root) / 'src/single_screen.c', anchor, guard + anchor)
