#include "../tools/frontend/touch_model.h"
#include <array>
#include <initializer_list>
#include <utility>
#include <cassert>
namespace RetunedFrontend {
inline bool NativeFrontendEnabled=true;
inline TouchSnapshot current;
inline TouchSnapshot SampleTouch(bool){return current;}
}
enum class NativeControlAction {A,B,X,Y,L,R,Zl,Zr,Select,Start,DpadUp,DpadDown,DpadLeft,DpadRight,Count};
constexpr int SDL_CONTROLLER_BUTTON_LEFTSTICK=7,SDL_CONTROLLER_BUTTON_RIGHTSTICK=8;
int SDL_GameControllerGetButton(void*,int){return 0;}
struct Host {std::array<bool,14> Actions{};int16_t LeftStickX=0,LeftStickY=0,RightStickX=0,RightStickY=0;};
Host inject(bool hostGuiVisible=false) {
 struct {void* Controller=nullptr;} selectedController;
 bool guestRefreshWillConsume=true;Host host;
 #include "../tools/frontend/touch_input.cpp.inc"
 return host;
}
int main(){
 RetunedFrontend::TouchModel model;model.SetAspect(16.f/9);
 model.Down(1,.16f,.72f);model.Motion(1,.16f,.64f);
 RetunedFrontend::current=model.Sample(true);
 auto host=inject();assert(host.LeftStickY>0); // Native physical-input contract: up is positive.
 model.Motion(1,.16f,.80f);RetunedFrontend::current=model.Sample(true);assert(inject().LeftStickY<0);
 RetunedFrontend::current.LookY=.75f;assert(inject().RightStickY>0);
 assert(inject(true).LeftStickY==0); // Menu navigation must not also move Link.
}
