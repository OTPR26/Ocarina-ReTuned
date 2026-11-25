#include "../tools/frontend/startup_layout.h"
#include <cassert>
#include <cmath>
int main() {
 using namespace RetunedFrontend;
 for(auto size: {std::pair{852.f,393.f},std::pair{667.f,375.f},std::pair{568.f,320.f}}) {
  auto menu=StartupLayout(size.first,size.second,1,20,true,true);
  assert(menu.Height>=44 && menu.TextScale>1 && !menu.ShowSetup);
  assert(menu.Top+3*menu.Height+2*menu.Gap<=size.second-55);
  assert(menu.Width>=200);
  assert(StartupLayout(size.first,size.second,1,20,true,false).ShowSetup);
 }
 for(auto size: {std::pair{667.f,375.f},std::pair{852.f,393.f},std::pair{1280.f,720.f}}) {
  auto menu=StartupLayout(size.first,size.second,1,20,true,true,102,38,true);
  assert(menu.TextScale>1.6f);
  assert(102*menu.TextScale+1.4f*menu.Height<=menu.Width+.01f);
  assert(20*menu.TextScale+12<=menu.Height);
 }
 auto docked=StartupLayout(1920,1080,1,20,false,true,102,42,true);
 assert(std::abs(docked.TextScale*20-42)<.01f);
 auto odin=StartupLayout(1920,1080,2,40,true,true);
 assert(odin.Height>=88 && !odin.ShowSetup);
}
