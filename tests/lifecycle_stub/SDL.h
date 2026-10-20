#pragma once
#include <algorithm>
#include <vector>
using Uint32=unsigned;
struct SDL_Event{Uint32 type=0;};
constexpr unsigned SDL_INIT_EVENTS=1,SDL_LOG_CATEGORY_RENDER=1;
constexpr Uint32 SDL_APP_WILLENTERBACKGROUND=10,SDL_APP_DIDENTERBACKGROUND=11,SDL_APP_WILLENTERFOREGROUND=12,SDL_APP_DIDENTERFOREGROUND=13;
using Watch=int(*)(void*,SDL_Event*);
inline std::vector<std::pair<Watch,void*>> watches;
inline int SDL_Init(unsigned){return 0;}
inline void SDL_Quit(){}
inline void SDL_AddEventWatch(Watch watch,void* data){watches.emplace_back(watch,data);}
inline void SDL_DelEventWatch(Watch watch,void* data){std::erase(watches,std::pair{watch,data});}
inline int SDL_PushEvent(SDL_Event* event){for(auto [watch,data]:watches)watch(data,event);return 1;}
inline void SDL_LogError(unsigned,const char*,const char*){}

inline void SDL_LogInfo(unsigned,const char*){}
