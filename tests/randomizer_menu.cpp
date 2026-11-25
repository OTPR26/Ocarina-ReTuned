#include "../tools/frontend/randomizer_model.h"
#include "../tools/frontend/settings_pages.h"
#include <cassert>
int main() {
    using namespace RetunedFrontend;
    RandomizerMenuState menu;
    assert(!menu.Available());
    assert(!CategoryVisible(SettingsPage::Randomizer, true, true));
    assert(CategoryVisible(SettingsPage::Randomizer, true, true, true));
    menu.Refresh = [] {};
    menu.Create = [](unsigned, const std::string&) {};
    menu.Start = [](unsigned) {};
    assert(menu.Available());
    assert(menu.CanCreate(0, true));
    assert(!menu.CanCreate(3, true));
    assert(!menu.CanCreate(0, false));
    menu.Slots[0].Status = RandomizerSlotStatus::Ready;
    assert(!menu.CanCreate(0, true));
    assert(menu.CanStart(0, true));
    assert(!menu.CanStart(0, false));
    menu.Busy = true;
    assert(!menu.CanStart(0, true));
    assert(!menu.CanCreate(1, true));
    menu.Busy = false;
    menu.Slots[0].Status = RandomizerSlotStatus::Unavailable;
    assert(!menu.CanStart(0, true));
    assert(!menu.CanCreate(0, true));
}
