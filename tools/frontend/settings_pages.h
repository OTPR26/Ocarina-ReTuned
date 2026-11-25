// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <array>
namespace RetunedFrontend {
enum class SettingsPage { General, Controls, Touch, Graphics, Audio, Hud, QualityOfLife, About, SaveStates, Advanced, SaveFiles, Mods, Cheats, Randomizer };
struct SettingsCategory { SettingsPage Page; const char* Label; const char* Description; };
inline constexpr std::array SettingsCategories{
 SettingsCategory{SettingsPage::General,"General","Make Ocarina ReTuned comfortable on your screen."},
 SettingsCategory{SettingsPage::Controls,"Controls","Map your controller and game controls."},
 SettingsCategory{SettingsPage::Touch,"Touch","Adjust touch controls and item icons."},
 SettingsCategory{SettingsPage::Graphics,"Graphics","Frame rate, camera, resolution and custom textures."},
 SettingsCategory{SettingsPage::Audio,"Audio","Sound and volume."},
 SettingsCategory{SettingsPage::Hud,"HUD","Adjust the HUD while keeping your chosen layout."},
 SettingsCategory{SettingsPage::QualityOfLife,"Quality of life","Small changes for a more comfortable adventure."},
 SettingsCategory{SettingsPage::Cheats,"Cheats","Optional resource cheats and inventory amounts."},
 SettingsCategory{SettingsPage::Mods,"Models","Player appearance and imported models."},
 SettingsCategory{SettingsPage::Randomizer,"Randomizer","Set up a new randomized adventure and view your current seed."},
 SettingsCategory{SettingsPage::About,"About","About Ocarina ReTuned and its contributors."},
 SettingsCategory{SettingsPage::SaveStates,"Save states","Manage save states."},
 SettingsCategory{SettingsPage::Advanced,"Advanced","Additional rendering options."},
 SettingsCategory{SettingsPage::SaveFiles,"Saves","Import, export, and choose a save folder."}
};
inline constexpr bool CategoryVisible(SettingsPage page,bool mobile,bool touch,bool randomizer=false) {
 if(page==SettingsPage::Randomizer)return randomizer;
 if(page==SettingsPage::SaveFiles){
#ifdef __ANDROID__
 return true;
#else
 return false;
#endif
 }
#ifdef RETUNED_SWITCH_DEKO
 if(page==SettingsPage::Touch||page==SettingsPage::Advanced)return false;
#endif
 if(page==SettingsPage::Touch)return touch;
 if(page==SettingsPage::SaveStates||page==SettingsPage::Advanced)return !mobile;
 return true;
}
}
