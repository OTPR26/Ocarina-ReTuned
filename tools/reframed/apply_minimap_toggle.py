"""Replace the native app's simulated D-pad hold with the game's map toggle."""
from pathlib import Path


def apply(root):
    root = Path(root)
    if 'Single Screen — EUR' not in (root / 'BUILD.txt').read_text():
        raise ValueError('Minimap toggle requires the canonical native source')
    path = root / 'src/input_remap.c'
    text = path.read_text()
    marker = '#include "minimap_toggle.h"\n'
    if marker not in text:
        start = text.index('// Vanilla OoT3D hides the minimap')
        end = text.index('#define HUD_SCALE_HOLD_FRAMES', start)
        text = text[:start] + text[end:]
        for line in ('static u16 sMinimapHideFrames = 0;\n',
                     'static u8 sMinimapAssumedVisible = 1;\n',
                     '        sMinimapHideFrames = 0;\n'):
            if text.count(line) != 1:
                raise ValueError('Minimap state context changed')
            text = text.replace(line, '')
        start = text.index('static void InputRemap_InjectMinimapButton(')
        end = text.index('static TouchPoint InputRemap_GetTouchPoint', start)
        text = text[:start] + text[end:]
        start = text.index('    // Complete an in-progress vanilla hide gesture')
        end = text.index('    InputRemap_UpdateHudScaleShortcut(irrstButtons);', start)
        # Older source copies sample here; manual-jump copies sample at entry.
        block = text[start:end]
        sample_start = block.find('    const u32 irrstButtons = irrstKeysHeld();')
        sample = ''
        if sample_start >= 0:
            sample_end = block.index('    if (irrstPressed & IRRST_BUTTON_ZL)', sample_start)
            sample = block[sample_start:sample_end]
        jump = next((line + '\n' for line in block.splitlines()
                     if 'ManualJump_Apply(' in line), '')
        replacement = sample + jump + '''    RetunedMinimap_Update(irrstPressed,
        globalCtx && gSaveContext.gameMode == 0 && gSaveContext.health &&
        *(volatile u32*)0x0050AF68 == 2 &&
        !InputRemap_IsItemsMenuOpen() && !InputRemap_IsSaveMenuOpen() &&
        !InputRemap_IsOcarinaUiOpen() && !InputRemap_IsGameOverUiOpen());

'''
        text = marker + text[:start] + replacement + text[end:]
    (root / 'include/minimap_toggle.h').write_bytes(
        Path(__file__).with_name('minimap_toggle.h').read_bytes())
    path.write_text(text)
