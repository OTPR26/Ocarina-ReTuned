#include "../tools/reframed/manual_jump_policy.h"
#include <assert.h>
int main(void) {
    const unsigned x=1u<<10,other=1u<<1;
    for(unsigned mode=0;mode<3;++mode)for(int gameplay=0;gameplay<2;++gameplay)
    for(int chord=0;chord<2;++chord)for(int xp=0;xp<2;++xp)for(int zp=0;zp<2;++zp) {
        const int expected=gameplay&&!chord&&((mode==1&&zp)||(mode==2&&xp));
        assert(!!ManualJump_Pressed(mode,gameplay,chord,xp,zp)==expected);
    }
    for(unsigned mode=0;mode<3;++mode)for(int gameplay=0;gameplay<2;++gameplay)
    for(int physical=0;physical<2;++physical)for(int zr=0;zr<2;++zr) {
        const unsigned original=other|(physical?x:0);
        const unsigned result=ManualJump_ItemMask(mode,gameplay,original,x,zr);
        assert(result&other);
        assert(!!(result&x)==(mode==2&&gameplay?zr:physical));
    }
    assert(ManualJump_ValidMode(99)==0);
    assert(!ManualJump_Pressed(1,1,0,0,0)); /* holding is not a new edge */
}
