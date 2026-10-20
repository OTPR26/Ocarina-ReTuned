#pragma once
#include <cstdint>
namespace RetunedFrontend {
inline bool RouteSettingsButton(uint32_t& buttons,uint32_t mask,bool& held,bool visible) {
    const bool down=(buttons&mask)!=0;
    const bool open=down && !held && !visible;
    held=down;buttons&=~mask;return open;
}
}
