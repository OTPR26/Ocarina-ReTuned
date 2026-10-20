#include "settings_button.h"
#include <cassert>
int main(){
 bool held=false;uint32_t buttons=0x19;
 assert(RetunedFrontend::RouteSettingsButton(buttons,8,held,false));assert(buttons==0x11);
 buttons=0x19;assert(!RetunedFrontend::RouteSettingsButton(buttons,8,held,false));assert(buttons==0x11);
 buttons=0;assert(!RetunedFrontend::RouteSettingsButton(buttons,8,held,false));
 buttons=8;assert(!RetunedFrontend::RouteSettingsButton(buttons,8,held,true));assert(buttons==0);
 buttons=0;RetunedFrontend::RouteSettingsButton(buttons,8,held,false);
 buttons=8;assert(RetunedFrontend::RouteSettingsButton(buttons,8,held,false));
}
