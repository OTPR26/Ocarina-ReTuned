#include "settings_button.h"
#include <cassert>
int main(){
 bool held=false;uint32_t buttons=0x19;bool visible=false;
 auto poll=[&](uint32_t input,bool capturing=false){buttons=input; if(RetunedFrontend::RouteSettingsButton(buttons,8,held,capturing))visible=!visible;};
 poll(0x19);assert(visible && buttons==0x11);
 poll(0x19);assert(visible && buttons==0x11); // Holding does not close immediately.
 poll(0);poll(8);assert(!visible && buttons==0); // Second press closes.
 poll(0);poll(8);assert(visible); // Third press reopens.
 poll(0);poll(8,true);assert(visible && buttons==0); // Remapping must not dismiss settings.
 poll(8,false);assert(visible); // A captured hold cannot become a toggle.
 poll(0);poll(8);assert(!visible);
}
