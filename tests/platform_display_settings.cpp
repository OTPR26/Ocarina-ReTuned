#include <cassert>
#include <cstdlib>
#include <map>
#include <string>
#include "platform_display_settings.h"

struct Config {
    std::map<std::string, bool> Values;
    unsigned Saves = 0;
    void SetBool(const char* key, bool value) { Values[key] = value; }
    void Save() { ++Saves; }
};

int main() {
    Config config;
    const auto toggle = [](const char* label, bool* value) {
        return ImGui::Checkbox(label, value);
    };
#ifdef TEST_DESKTOP
    RetunedFrontend::DrawPlatformDisplaySettings(&config, toggle);
    assert(ImGui::Labels.empty() && config.Saves == 0);
#else
    using namespace RetunedFrontend;
#ifdef RETUNED_ANDROID_DISPLAY_SETTINGS
    setenv("RETUNED_SCREEN_PROBE", "android-dual", 1);
    AndroidDualSelected = true;
    AndroidLowerAvailable = false;
#else
    DuoDisplayGeometry geometry;
    geometry.Available = true;
    DuoDisplay.Publish(geometry);
    DuoDisplay.Select(ScreenPreference::Dual);
#endif
    DrawPlatformDisplaySettings(&config, toggle);
    assert(ImGui::Saw("Screen mode") && ImGui::Saw("Bottom equipment panel"));
    ImGui::Labels.clear();
    ImGui::NextMode = 0;
    DrawPlatformDisplaySettings(&config, toggle);
    assert(!config.Values.at("Interface.DualScreen"));
    assert(!ImGui::Saw("Bottom equipment panel"));
#ifdef RETUNED_ANDROID_DISPLAY_SETTINGS
    assert(!AndroidDualSelected.load());
#else
    assert(DuoDisplay.Preference() == ScreenPreference::Single);
#endif
    ImGui::NextMode = 1;
    ImGui::ChangePanel = true;
    DrawPlatformDisplaySettings(&config, toggle);
    assert(config.Values.at("Interface.DualScreen"));
    assert(!config.Values.at("Interface.DualEquipmentPanel"));
    assert(!LowerEquipmentPanelEnabled.load() && config.Saves == 3);
#endif
}
