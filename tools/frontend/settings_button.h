#pragma once
#include <cstdint>
namespace RetunedFrontend {
inline bool RouteSettingsButton(uint32_t& buttons,uint32_t mask,bool& held,bool bindingCaptureActive) {
    const bool down=(buttons&mask)!=0;
    const bool toggle=down && !held && !bindingCaptureActive;
    held=down;buttons&=~mask;return toggle;
}
}
