#include "../tools/frontend/settings_pages.h"
#include <cassert>
#include <string_view>
#include <vector>
int main(){
 using namespace RetunedFrontend;
 std::vector<std::string_view> mobile;
 for(const auto& category:SettingsCategories)if(CategoryVisible(category.Page,true,true))mobile.push_back(category.Label);
 const std::vector<std::string_view> expected{"General","Controls","Touch","Graphics","Audio","HUD","Quality of life","About"};
 assert(mobile==expected);
 for(size_t i=0;i<SettingsCategories.size();++i)for(size_t j=i+1;j<SettingsCategories.size();++j){
  assert(SettingsCategories[i].Page!=SettingsCategories[j].Page);
  assert(std::string_view(SettingsCategories[i].Label)!=SettingsCategories[j].Label);
 }
 assert(!CategoryVisible(SettingsPage::Touch,true,false));
 assert(CategoryVisible(SettingsPage::SaveStates,false,false));
 assert(!CategoryVisible(SettingsPage::Advanced,true,true));
}
