// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <SDL.h>
#include <atomic>
#include <functional>
#include <exception>
namespace RetunedFrontend {
class MobileLifecycleGate {
 std::atomic<bool> active{true};
 std::function<void()> pauseGpu,resumeGpu;
 static int Watch(void* data,SDL_Event* event) {
  auto& gate=*static_cast<MobileLifecycleGate*>(data);
  try {
   if(event->type==SDL_APP_WILLENTERBACKGROUND&&gate.active.exchange(false)){gate.pauseGpu();SDL_LogInfo(SDL_LOG_CATEGORY_RENDER,"Display lifecycle: GPU paused");}
   if(event->type==SDL_APP_DIDENTERFOREGROUND&&!gate.active.load()){gate.resumeGpu();gate.active=true;SDL_LogInfo(SDL_LOG_CATEGORY_RENDER,"Display lifecycle: GPU resumed");}
  } catch(const std::exception& error){SDL_LogError(SDL_LOG_CATEGORY_RENDER,"Display lifecycle: %s",error.what());}
  return 1;
 }
public:
 MobileLifecycleGate(std::function<void()> pause,std::function<void()> resume):pauseGpu(std::move(pause)),resumeGpu(std::move(resume)){SDL_AddEventWatch(Watch,this);}
 ~MobileLifecycleGate(){SDL_DelEventWatch(Watch,this);}
 bool Active()const{return active.load();}
};
}
