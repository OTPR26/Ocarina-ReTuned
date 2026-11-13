from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HudGroupSizesTests(unittest.TestCase):
    def test_native_group_scaling(self):
        source = os.environ.get('RETUNED_REFRAMED_SOURCE')
        if not source:
            self.skipTest('Requires staged native source')
        compiler = shutil.which('clang') or shutil.which('cc')
        if not compiler:
            self.skipTest('Requires C compiler')
        text = (Path(source) / 'src/native_hud.c').read_text()
        start = text.index('static u32 sNativeHudGroupScale')
        helper = text[start:text.index('static void NativeHud_RebuildPositions', start)]
        start = text.index('u32 NativeHud_GetGroupScale')
        exports = text[start:text.index('static u32 NativeHud_UvHash', start)]
        with tempfile.TemporaryDirectory() as directory:
            c = Path(directory) / 'sizes.c'
            c.write_text('''#include <assert.h>
#include <math.h>
typedef unsigned u32;
static int sNativeHudDualMenuLayout,sNativeHudOcarinaLayout;
static float gNativeHudPositions[97*12];
#define p ((float (*)[12])gNativeHudPositions)
static void NativeHud_ScaleQuad(u32 q,float x,float y,float s){for(u32 v=0;v<4;++v){p[q][v*3]=x+(p[q][v*3]-x)*s;p[q][v*3+1]=y+(p[q][v*3+1]-y)*s;}}
static void NativeHud_TranslateQuad(u32 q,float x,float y){for(u32 v=0;v<4;++v){p[q][v*3]+=x;p[q][v*3+1]+=y;}}
static void NativeHud_ScaleQuadRange(u32 a,u32 b,float x,float y,float s){for(u32 q=a;q<=b;++q)NativeHud_ScaleQuad(q,x,y,s);}
''' + helper + '''
static void NativeHud_RebuildPositions(void){for(u32 q=0;q<97;++q){for(u32 v=0;v<4;++v){p[q][v*3]=100+2*v;p[q][v*3+1]=100;}}NativeHud_ScaleGroups();}
''' + exports + '''
int main(void){
 assert(NativeHud_GetGroupScale(0)==100&&NativeHud_GetGroupScale(1)==100);
 NativeHud_RebuildPositions();assert(p[4][0]==8&&p[4][1]==100);
 for(u32 d=50;d<=125;d+=25)for(u32 a=50;a<=125;a+=25){
  NativeHud_SetGroupScale(0,d);NativeHud_SetGroupScale(1,a);NativeHud_RebuildPositions();
  for(u32 q=0;q<97;++q){
   const int dp=q==4||(q>=8&&q<=12)||q==23;
   const int ac=(q>=1&&q<=3)||(q>=5&&q<=7)||q==28||q==29||(q>=33&&q<=96);
   const float expectedX=dp?8:ac?400-300*a/100.f:100;
   assert(fabsf((p[q][3]-p[q][0])-2*(dp?d/100.f:ac?a/100.f:1))<.001f);
   const float expectedY=dp?67.5f+32.5f*d/100.f:ac?a:100;
   assert(fabsf(p[q][0]-expectedX)<.001f&&fabsf(p[q][1]-expectedY)<.001f);
  }
 }
 NativeHud_SetGroupScale(0,150);NativeHud_SetGroupScale(1,150);NativeHud_SetGroupScale(1,99);NativeHud_SetGroupScale(2,50);
 assert(NativeHud_GetGroupScale(0)==125&&NativeHud_GetGroupScale(1)==125&&NativeHud_GetGroupScale(2)==100);
 sNativeHudDualMenuLayout=1;NativeHud_RebuildPositions();for(u32 q=0;q<97;++q)assert(p[q][0]==100&&p[q][1]==100);
 sNativeHudDualMenuLayout=0;sNativeHudOcarinaLayout=1;NativeHud_RebuildPositions();
 for(u32 q=0;q<97;++q){const int dp=q==4||(q>=8&&q<=11)||q==23;
  assert(fabsf((p[q][3]-p[q][0])-2*(dp?1.25f:1.f))<.001f);
  assert(fabsf(p[q][0]-(dp?8:100))<.001f);
 }
 assert(p[12][0]==100); // Ocarina reuses this cell for the action-button base.
 return 0;
}
''')
            exe = Path(directory) / 'sizes'
            subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', str(c), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)
