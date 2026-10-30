// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <SDL.h>
#include "three_ds_input.h"
#include <array>
#include <mutex>

namespace RetunedFrontend {
inline std::array<float,3> OrientDeviceMotion(std::array<float,3> value,
                                             SDL_DisplayOrientation orientation) {
    switch(orientation) {
    case SDL_ORIENTATION_LANDSCAPE: return {-value[1],value[0],value[2]};
    case SDL_ORIENTATION_LANDSCAPE_FLIPPED: return {value[1],-value[0],value[2]};
    case SDL_ORIENTATION_PORTRAIT_FLIPPED: return {-value[0],-value[1],value[2]};
    default: return value;
    }
}

class MobileDeviceMotion {
    std::mutex mutex;
    SDL_Sensor *accelerometer=nullptr,*gyroscope=nullptr;
    bool initialized=false,suspended=false;

    void Close() {
        if(SDL_WasInit(SDL_INIT_SENSOR)) {
            if(accelerometer)SDL_SensorClose(accelerometer);
            if(gyroscope)SDL_SensorClose(gyroscope);
        }
        accelerometer=gyroscope=nullptr;
    }
    static int Watch(void* context,SDL_Event* event) {
        auto& self=*static_cast<MobileDeviceMotion*>(context);
        if(event->type==SDL_APP_WILLENTERBACKGROUND || event->type==SDL_APP_TERMINATING) {
            std::lock_guard lock(self.mutex);
            self.suspended=true;
            self.Close();
        } else if(event->type==SDL_APP_DIDENTERFOREGROUND) {
            std::lock_guard lock(self.mutex);
            self.suspended=false;
        }
        return 1;
    }
public:
    MobileDeviceMotion(){SDL_AddEventWatch(Watch,this);}
    ~MobileDeviceMotion(){
        if(SDL_WasInit(SDL_INIT_EVENTS))SDL_DelEventWatch(Watch,this);
        if(SDL_WasInit(SDL_INIT_SENSOR)) {
            Close();
            if(initialized)SDL_QuitSubSystem(SDL_INIT_SENSOR);
        }
    }
    void Sample(ThreeDsRecomp::Input::MotionObservation& motion,bool enabled) {
        std::lock_guard lock(mutex);
        // A connected controller retains ownership of its own motion sensors.
        if(!enabled || suspended || motion.GyroscopeValid){Close();return;}
        if(!initialized) {
            if(SDL_InitSubSystem(SDL_INIT_SENSOR)!=0)return;
            initialized=true;
        }
        for(int index=0;index<SDL_NumSensors();++index) {
            const auto type=SDL_SensorGetDeviceType(index);
            if(type==SDL_SENSOR_ACCEL && !accelerometer)accelerometer=SDL_SensorOpen(index);
            if(type==SDL_SENSOR_GYRO && !gyroscope)gyroscope=SDL_SensorOpen(index);
        }
        std::array<float,3> accel{},gyro{};
        const bool hasAccel=accelerometer && SDL_SensorGetData(accelerometer,accel.data(),3)==0;
        const bool hasGyro=gyroscope && SDL_SensorGetData(gyroscope,gyro.data(),3)==0;
        const auto orientation=SDL_GetDisplayOrientation(0);
        auto sample=ThreeDsRecomp::Input::ConvertSdlMotion(
            OrientDeviceMotion(accel,orientation),hasAccel,
            OrientDeviceMotion(gyro,orientation),hasGyro);
        if(sample.GyroscopeValid || !motion.AccelerometerValid)motion=sample;
    }
};

inline void SampleMobileDeviceMotion(ThreeDsRecomp::Input::MotionObservation& motion,bool enabled) {
#if defined(__ANDROID__) || defined(__IPHONEOS__)
    static MobileDeviceMotion device;
    device.Sample(motion,enabled);
#else
    (void)motion;(void)enabled;
#endif
}
}
