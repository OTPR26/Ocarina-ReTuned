from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

HARNESS = r"""
#include <stdint.h>
#include <string.h>
#include <assert.h>
typedef uint32_t u32;
typedef uint8_t u8;
typedef void (*FinishTopPassFn)(void*);
static int active = 1;
static u8 sFileGuidanceVisible = 1;
static u32 width, height, calls, seenWidth[4], seenHeight[4];
static u32* seenNode[4];
static int IsFilePresentationActive(void) { return active; }
static void SetViewport(u32 x, int y, u32 w, int h) { width = w; height = h; }
static void MockDraw(void* pass) {
    assert(calls < 4);
    seenWidth[calls] = width; seenHeight[calls] = height;
    seenNode[calls] = ((u32**)((uint8_t*)pass + 0x394))[0]; calls++;
}
#define BOARD_VTABLE_ADDR 0x12345678u
#define DRAW_FILE_LOGO_ADDR ((uintptr_t)&MockDraw)
"""
CASES = r"""
static uint8_t pass[0x800];
static u32 fade[100], logo[100];
static void setup(u32 count) {
    memset(pass,0,sizeof pass);memset(fade,0,sizeof fade);memset(logo,0,sizeof logo);
    *(u32*)(pass+0x24)=count;
    ((u32**)(pass+0x394))[0]=fade;
    ((u32**)(pass+0x394))[1]=logo;
    fade[0]=logo[0]=BOARD_VTABLE_ADDR;
    float x=200,y=120;
    memcpy(&fade[15],&x,4);memcpy(&fade[16],&y,4);
    active=1; calls=0; width=17;height=19;
}
int main(void) {
    setup(1);SingleScreen_DrawFileLogoPass(pass);
    assert(calls==1 && seenWidth[0]==480 && seenHeight[0]==400);
    assert(*(u32*)(pass+0x24)==1 && ((u32**)(pass+0x394))[0]==fade);
    setup(2);
    ((u32**)(pass+0x394))[0]=logo;((u32**)(pass+0x394))[1]=fade;
    fade[1]=0x100000;logo[1]=fade[1]+0x1c8;
    SingleScreen_DrawFileLogoPass(pass);
    assert(calls==2 && seenWidth[0]==324 && seenHeight[0]==324);
    assert(seenWidth[1]==480 && seenHeight[1]==400);
    assert(seenNode[0]==logo && seenNode[1]==fade);
    assert(*(u32*)(pass+0x24)==2 && ((u32**)(pass+0x394))[0]==logo);
    setup(1);((u32**)(pass+0x394))[0]=logo;
    SingleScreen_DrawFileLogoPass(pass);
    assert(calls==1 && seenWidth[0]==324 && seenHeight[0]==324);
    setup(1);fade[0]=0x999;
    SingleScreen_DrawFileLogoPass(pass);
    assert(calls==1 && seenWidth[0]==324);
    setup(1);active=0;
    SingleScreen_DrawFileLogoPass(pass);
    assert(calls==1 && seenWidth[0]==17 && seenHeight[0]==19);
    setup(0);((u32**)(pass+0x394))[0]=0;
    SingleScreen_DrawFileLogoPass(pass);
    assert(calls==1);
    return 0;
}
"""

class FileSelectionFadeTests(unittest.TestCase):
    def test_actual_draw_pass_preserves_fade_logo_and_other_scenes(self):
        source = ROOT/'work/reference/reframed/release-source/2.0.2/single/EUR/src/single_screen.c'
        compiler = shutil.which('cc')
        if not source.is_file() or not compiler:
            self.skipTest('Requires the pinned ReFramed source and a C compiler')
        sys.path[:0] = [str(ROOT/'tools/reframed')]
        from apply_file_selection_fade import apply
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'src').mkdir()
            path=root/'src/single_screen.c';path.write_bytes(source.read_bytes())
            apply(root);patched=path.read_text();apply(root)
            self.assertEqual(path.read_text(),patched)
            start=patched.index('void SingleScreen_DrawFileLogoPass(void* pass) {')
            end=patched.index('{',start)+1;depth=1
            while depth:
                depth+=(patched[end]=='{')-(patched[end]=='}');end+=1
            (root/'check.c').write_text(HARNESS+patched[start:end]+CASES)
            result=subprocess.run([compiler,'-std=c11','-O0','-fno-strict-aliasing',str(root/'check.c'),'-o',str(root/'check')],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr.decode())
            subprocess.run([str(root/'check')],check=True,capture_output=True)
