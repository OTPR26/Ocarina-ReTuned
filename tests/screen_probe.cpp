#include "retuned_screen_probe.h"
#include <cassert>
#include <stdexcept>
using namespace RetunedFrontend;
static void Mode(const char* value){
#ifdef _WIN32
 _putenv_s("RETUNED_SCREEN_PROBE",value);
#else
 setenv("RETUNED_SCREEN_PROBE",value,1);
#endif
}
int main(){
 Mode("");assert(!ScreenProbeEnabled());
 assert(ProbeOutputWidth(1200,720)==1200 && ProbeOutputHeight(1200,720)==720);
 Mode("unknown");assert(!ScreenProbeEnabled());
 for(auto mode:{"stacked","side-by-side"}){
  Mode(mode);assert(ScreenProbeEnabled());
  auto logical=ScreenProbeLayout(1200,720);
  for(float scale:{1.f,1.5f,2.f,3.f}){
   auto pixels=ScreenProbeLayout(1200*scale,720*scale);
   assert(std::abs(pixels.Lower.X-logical.Lower.X*scale)<.001f);
   assert(std::abs(pixels.Lower.Y-logical.Lower.Y*scale)<.001f);
   const float x=logical.Lower.X+logical.Lower.Width*.31f;
   const float y=logical.Lower.Y+logical.Lower.Height*.67f;
   auto a=MapLowerScreenTouch(logical,x,y),b=MapLowerScreenTouch(pixels,x*scale,y*scale);
   assert(a && b && a->X==b->X && a->Y==b->Y);
  }
 }
 assert(ProbeScanoutScreen==GameScreen::Top);
 try{ProbeScanoutScope scope(GameScreen::Lower);assert(ProbeScanoutScreen==GameScreen::Lower);throw std::runtime_error("render failure");}
 catch(const std::runtime_error&){}
 assert(ProbeScanoutScreen==GameScreen::Top);
 Mode("");
}
