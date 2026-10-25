#include "screen_presentation_bridge.h"
#include <cassert>
#include <vector>
using namespace RetunedFrontend;
int main() {
    ScreenPresentationBridge bridge;
    unsigned calls = 0, state = 0;
    bool busy = true, fail = false, lie = false;
    const auto invoke = [&](uint32_t entry, std::optional<uint32_t> argument)
            -> std::optional<uint32_t> {
        ++calls;
        if (fail) return {};
        if (entry == 0x600000) { assert(!argument); return state; }
        assert(entry == 0x600004 && argument);
        if (busy) return 0;
        if (!lie) state = *argument;
        return 1;
    };
    assert(!bridge.Update(GamePresentation::Dual, invoke) && !calls);
    for (auto schema : {0u, 2u}) {
        bridge.Bind(schema, 0x600000, 0x600004);
        assert(!bridge.Supported());
    }
    bridge.Bind(1, 0x600000, 0x600000);
    assert(!bridge.Supported());
    bridge.Bind(1, 0x600001, 0x600004);
    assert(!bridge.Supported());
    bridge.Bind(1, 0x600000, 0x600004);
    assert(bridge.Supported());
    assert(!bridge.Update(GamePresentation::Dual, invoke));
    assert(bridge.Effective() == GamePresentation::Single);
    busy = false;
    lie = true;
    assert(!bridge.Update(GamePresentation::Dual, invoke));
    assert(bridge.Effective() == GamePresentation::Single);
    assert(bridge.Faulted());
    bridge.Bind(1, 0x600000, 0x600004);
    lie = false;
    assert(bridge.Update(GamePresentation::Dual, invoke));
    assert(bridge.Effective() == GamePresentation::Dual);
    fail = true;
    assert(!bridge.Update(GamePresentation::Single, invoke));
    assert(bridge.Effective() == GamePresentation::Dual);
    assert(bridge.Faulted());
    bridge.Bind(1, 0x600000, 0x600004);
    fail = false;
    state = 2;
    assert(!bridge.Update(GamePresentation::Single, invoke));
    assert(bridge.Faulted());
    bridge.Bind(1, 0x600000, 0x600004);
    state = 1;
    assert(bridge.Update(GamePresentation::Single, invoke));
    assert(bridge.Effective() == GamePresentation::Single);
    bridge.Bind(0, 0, 0);
    assert(!bridge.Supported() && bridge.Effective() == GamePresentation::Single);
}
