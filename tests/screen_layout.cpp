#include "screen_layout.h"
#include <cassert>
#include <limits>
#include <utility>
using namespace RetunedFrontend;
static bool Near(float a,float b){return std::abs(a-b)<.001f;}
int main(){
 for(auto mode:{ScreenArrangement::Stacked,ScreenArrangement::SideBySide})
  for(auto size:{std::pair{800.f,1000.f},std::pair{1920.f,1080.f},std::pair{600.f,800.f}}){
   auto layout=LayoutGameScreens(size.first,size.second,mode);
   for(auto rect:{layout.Top,layout.Lower}){
    assert(rect.Width>0 && rect.Height>0 && rect.X>=0 && rect.Y>=0);
    assert(rect.X+rect.Width<=size.first+.001f && rect.Y+rect.Height<=size.second+.001f);
   }
   assert(Near(layout.Top.Width/layout.Top.Height,400.f/240.f));
   assert(Near(layout.Lower.Width/layout.Lower.Height,320.f/240.f));
   auto lower=layout.Lower;
   auto center=MapLowerScreenTouch(layout,lower.X+lower.Width*.5f,lower.Y+lower.Height*.5f);
   assert(center && center->X>=159 && center->X<=160 && center->Y>=119 && center->Y<=120);
   auto origin=MapLowerScreenTouch(layout,lower.X,lower.Y);assert(origin && origin->X==0 && origin->Y==0);
   assert(!MapLowerScreenTouch(layout,lower.X+lower.Width,lower.Y));
   assert(!MapLowerScreenTouch(layout,lower.X,lower.Y+lower.Height));
   assert(!MapLowerScreenTouch(layout,layout.Top.X+layout.Top.Width*.5f,layout.Top.Y+layout.Top.Height*.5f));
  }
 auto single=LayoutGameScreens(1200,900,ScreenArrangement::Single);
 assert(single.Lower.Width==0 && !MapLowerScreenTouch(single,600,750));
 assert(Near(single.Top.Width/single.Top.Height,400.f/240.f));
 assert(LayoutGameScreens(-1,900,ScreenArrangement::Stacked).Top.Width==0);
 assert(LayoutGameScreens(900,std::numeric_limits<float>::quiet_NaN(),ScreenArrangement::Stacked).Top.Width==0);
 auto zero=LayoutGameScreens(10,10,ScreenArrangement::Stacked,400.f/240.f,20);
 assert(zero.Lower.Height==0 && !MapLowerScreenTouch(zero,0,0));
}
