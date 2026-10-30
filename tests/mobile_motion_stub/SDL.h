#pragma once
#include <algorithm>
#include <array>
#include <vector>
using Uint32=unsigned;
constexpr unsigned SDL_INIT_SENSOR=1,SDL_INIT_EVENTS=2;
constexpr unsigned SDL_APP_WILLENTERBACKGROUND=10,SDL_APP_DIDENTERFOREGROUND=11,SDL_APP_TERMINATING=12;
enum SDL_DisplayOrientation {SDL_ORIENTATION_UNKNOWN,SDL_ORIENTATION_LANDSCAPE,SDL_ORIENTATION_LANDSCAPE_FLIPPED,SDL_ORIENTATION_PORTRAIT,SDL_ORIENTATION_PORTRAIT_FLIPPED};
enum SDL_SensorType {SDL_SENSOR_ACCEL,SDL_SENSOR_GYRO};
struct SDL_Event {unsigned type;};
struct SDL_Sensor {SDL_SensorType type;std::array<float,3> data;bool fail=false;};
namespace FakeMotion {
inline unsigned initialized=SDL_INIT_EVENTS;
inline int count=2,open=0;
inline SDL_DisplayOrientation orientation=SDL_ORIENTATION_PORTRAIT;
inline SDL_Sensor sensors[]={{SDL_SENSOR_ACCEL,{0,9.80665f,0}},{SDL_SENSOR_GYRO,{1,2,3}}};
struct Watch {int(*call)(void*,SDL_Event*);void* context;};
inline std::vector<Watch> watches;
inline void Send(unsigned type){SDL_Event event{type};auto copy=watches;for(auto w:copy)w.call(w.context,&event);}
}
inline unsigned SDL_WasInit(unsigned flags){return FakeMotion::initialized&flags;}
inline int SDL_InitSubSystem(unsigned flags){FakeMotion::initialized|=flags;return 0;}
inline void SDL_QuitSubSystem(unsigned flags){FakeMotion::initialized&=~flags;}
inline int SDL_NumSensors(){return FakeMotion::count;}
inline SDL_SensorType SDL_SensorGetDeviceType(int index){return FakeMotion::sensors[index].type;}
inline SDL_Sensor* SDL_SensorOpen(int index){++FakeMotion::open;return &FakeMotion::sensors[index];}
inline void SDL_SensorClose(SDL_Sensor*){--FakeMotion::open;}
inline int SDL_SensorGetData(SDL_Sensor* sensor,float* data,int){if(sensor->fail)return -1;std::copy(sensor->data.begin(),sensor->data.end(),data);return 0;}
inline SDL_DisplayOrientation SDL_GetDisplayOrientation(int){return FakeMotion::orientation;}
inline void SDL_AddEventWatch(int(*callback)(void*,SDL_Event*),void* context){FakeMotion::watches.push_back({callback,context});}
inline void SDL_DelEventWatch(int(*callback)(void*,SDL_Event*),void* context){std::erase_if(FakeMotion::watches,[&](auto w){return w.call==callback && w.context==context;});}
