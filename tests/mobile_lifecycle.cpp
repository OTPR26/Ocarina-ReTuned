#include "../tools/frontend/mobile_lifecycle.h"
#include <cassert>
int main() {
 assert(SDL_Init(SDL_INIT_EVENTS)==0);
 int paused=0,resumed=0;
 auto send=[](Uint32 type){SDL_Event e{};e.type=type;assert(SDL_PushEvent(&e)>=0);};
 {
  RetunedFrontend::MobileLifecycleGate gate([&]{++paused;},[&]{++resumed;});
  assert(gate.Active());send(SDL_APP_WILLENTERBACKGROUND);
  assert(!gate.Active()&&paused==1);
  send(SDL_APP_WILLENTERBACKGROUND);send(SDL_APP_DIDENTERBACKGROUND);
  assert(!gate.Active()&&paused==1);
  send(SDL_APP_WILLENTERFOREGROUND);assert(!gate.Active()&&resumed==0);
  send(SDL_APP_DIDENTERFOREGROUND);assert(gate.Active()&&resumed==1);
  send(SDL_APP_DIDENTERFOREGROUND);assert(resumed==1);
 }
 send(SDL_APP_WILLENTERBACKGROUND);assert(paused==1);
 SDL_Quit();
}
