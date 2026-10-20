#include "ocarina_lifecycle.h"
#include <cassert>
int main(){
 RetunedFrontend::OcarinaShortcutLifecycle state;
 assert(!state.Finished(false,false));
 for(int i=0;i<120;++i)assert(!state.Finished(true,false));
 for(int i=0;i<600;++i)assert(!state.Finished(true,true));
 assert(state.Finished(true,false));assert(!state.Finished(true,false));
 assert(!state.Finished(false,false));assert(!state.Finished(true,false));
 assert(!state.Finished(true,true));assert(!state.Finished(false,false));
 assert(!state.Finished(true,false));
}
