#include "../tools/frontend/movement_stick.h"
#include <cassert>

int main() {
    using RetunedFrontend::MapMovementStick;
    assert((MapMovementStick(0,0,18,154)==std::array<std::int16_t,2>{0,0}));
    assert((MapMovementStick(-2711,-2116,18,154)==std::array<std::int16_t,2>{0,0}));
    assert((MapMovementStick(-32768,0,18,154)==std::array<std::int16_t,2>{-154,0}));
    // At full deflection, direction changes must not introduce an extra slowdown.
    for (int degree=0; degree<360; ++degree) {
        const double angle=degree*3.141592653589793/180;
        auto v=MapMovementStick(std::lround(32767*std::cos(angle)),
                               std::lround(32767*std::sin(angle)),18,154);
        assert(std::abs(std::hypot(v[0],v[1])-154)<1);
    }
    auto v=MapMovementStick(32767,32767,18,154);
    assert(std::hypot(v[0],v[1])<155); // Square-range devices cannot gain diagonal speed.
    v=MapMovementStick(0,16384,18,154);
    assert(v[0]==0 && v[1]>59 && v[1]<62); // Retain intentional slow walking.
}
