"""Stage the canonical native manual-jump experiment; default remains Off."""
from pathlib import Path


def apply(root: Path):
    root=Path(root)
    if 'Single Screen — EUR' not in (root/'BUILD.txt').read_text():
        raise ValueError('Manual jump requires the canonical native EUR-addressed source')
    here=Path(__file__).parent
    for name,directory in [('manual_jump.h','include'),('manual_jump.c','src'),('manual_jump_policy.h','include'),('manual_jump_hud.h','include')]:
        (root/directory/name).write_bytes((here/name).read_bytes())
    p=root/'src/input_remap.c';text=p.read_text();marker='#include "manual_jump.h"\n'
    call='    ManualJump_Apply(globalCtx,hidPad,gameHeld,gamePressed,gameReleased,irrstButtons,irrstPressed,irrstReleased);'
    if marker not in text:
        text=marker+text
    # Sample extended-button edges before any modal early return. Leaving a
    # menu while holding ZR must not synthesize a new jump press.
    old="""    const u32 irrstButtons = irrstKeysHeld();
    const u32 irrstPressed = irrstButtons & ~sPreviousIrrstButtons;"""
    sample=old+"""
    const u32 irrstReleased = sPreviousIrrstButtons & ~irrstButtons;
    sPreviousIrrstButtons = irrstButtons;"""
    # Upgrade the initial experiment without duplicating samples/calls.
    text=text.replace(old+"\n    const u32 irrstReleased = sPreviousIrrstButtons & ~irrstButtons;\n    sPreviousIrrstButtons = irrstButtons;\n"+call,old+"\n    sPreviousIrrstButtons = irrstButtons;")
    if call not in text:
        before=old+"\n    sPreviousIrrstButtons = irrstButtons;"
        if text.count(before)!=1:raise ValueError('Extended input edge context changed')
        text=text.replace(before,call)
        entry='void InputRemap_Update(GlobalContext* globalCtx) {'
        if text.count(entry)!=1:raise ValueError('Input update entry changed')
        text=text.replace(entry,entry+'\n'+sample)
    p.write_text(text)
    p=root/'src/native_hud.c';text=p.read_text()
    if '#include "manual_jump_hud.h"' not in text:
        text='#include "manual_jump.h"\n#include "manual_jump_hud.h"\n'+text
        point='static void NativeHud_RebuildPositions(void) {'
        helper='''static u8 sManualJumpBumper;
static void NativeHud_PositionJumpBumper(void) {
    if(!sManualJumpBumper)return;
    NativeHud_CollapseQuad(2);
    /* Keep the remaining Y/A/B triangle together, above and to the left.
     * The remapped item occupies the compact shoulder beside its top row. */
    NativeHud_TranslateQuad(1,-30.0f,-17.0f);
    NativeHud_TranslateQuad(3,-30.0f,-17.0f);
    NativeHud_TranslateQuad(5,-30.0f,-17.0f);
    NativeHud_TranslateQuad(7,-30.0f,-17.0f);
    NativeHud_TranslateQuad(29,-30.0f,-17.0f);
    NativeHud_SetQuadRect(6,377.0f,24.0f,385.0f,16.0f);
    NativeHud_SetQuadRect(28,385.0f,25.0f,392.0f,21.0f);
    for(u32 i=0;i<64;++i) {
        const float* p=ManualJump_BumperPatches[i];
        float* out=gNativeHudPositions+(33+i)*12;
        for(u32 vertex=0;vertex<4;++vertex) {
            out[vertex*3]=p[vertex*2];out[vertex*3+1]=p[vertex*2+1];out[vertex*3+2]=0;
        }
    }
}
'''
        if text.count(point)!=1:raise ValueError('HUD position entry changed')
        text=text.replace(point,helper+point)
        point='    if (sNativeHudDualMenuLayout) {'
        if text.count(point)!=1:raise ValueError('HUD gameplay position context changed')
        text=text.replace(point,'    NativeHud_PositionJumpBumper();\n'+point)
        point='    NativeHud_ScaleQuadRange(1, 3, 400.0f, 0.0f, scale);'
        text=text.replace(point,'    NativeHud_ScaleQuadRange(33, 96, 400.0f, 0.0f, scale);\n'+point)
        point='    // These are the live values used by the current second-screen I/II'
        uv='''    for(u32 i=0;i<64;++i) {
        float* uv=gNativeHudUVs+(33+i)*8;
        const float u=66.5f/512.0f;
        const float v=1.0f-3.5f/256.0f;
        for(u32 vertex=0;vertex<4;++vertex){uv[vertex*2]=u;uv[vertex*2+1]=v;}
    }
'''
        if text.count(point)!=1:raise ValueError('HUD live atlas context changed')
        text=text.replace(point,uv+point)
        point='    const u8 dual = ScreenPresentation_IsDual();'
        text=text.replace(point,point+'\n    const u8 bumper=ManualJump_Get()==2 && !InputRemap_IsItemsMenuOpen() &&\n        !InputRemap_IsSaveMenuOpen() && !InputRemap_IsOcarinaUiOpen();\n    if(bumper!=sManualJumpBumper){sManualJumpBumper=bumper;NativeHud_RebuildPositions();}')
        point='        float targetCenterY = (isActionText ? 40.0f : 37.0f) * hudScale;'
        if text.count(point)!=1:raise ValueError('Action-button position context changed')
        text=text.replace(point,point+'\n        if(sManualJumpBumper){targetCenterX-=30.0f*hudScale;targetCenterY-=17.0f*hudScale;}')
        # Draw the extra shoulder patches before the equipped-item quads.
        # The strip connector must reference the actual preceding quad.
        start=text.index('u16 gNativeHudIndices[')
        opening=text.index('{',start);end=text.index('};',opening)
        order=list(range(5))+list(range(33,97))+list(range(5,33))+list(range(97,106))
        indices=[0,1,2,3];previous=0
        for quad in order[1:]:
            indices.extend([previous*4+3,quad*4,quad*4,quad*4+1,quad*4+2,quad*4+3]);previous=quad
        rows=['    '+', '.join(str(n) for n in indices[i:i+16])+',' for i in range(0,len(indices),16)]
        text=text[:opening+1]+'\n'+'\n'.join(rows)+'\n'+text[end:]
        p.write_text(text)
