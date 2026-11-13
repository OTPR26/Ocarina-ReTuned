// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#if defined(__ANDROID__)
#include <SDL_system.h>
#include <jni.h>
namespace RetunedFrontend {
inline void SampleAndroidControllerMotion(ThreeDsRecomp::Input::MotionObservation& motion,
                                         SDL_GameController* controller, bool enabled) {
    auto* env=static_cast<JNIEnv*>(SDL_AndroidGetJNIEnv());
    if(!env || env->PushLocalFrame(8)<0)return;
    jobject activity=static_cast<jobject>(SDL_AndroidGetActivity());
    if(activity) {
        jclass type=env->GetObjectClass(activity);
        jmethodID method=env->GetMethodID(type,"retunedControllerMotion","(Ljava/lang/String;II)[D");
        if(method) {
            bool use=enabled && controller && !motion.GyroscopeValid;
            const char* name=use?SDL_GameControllerName(controller):"";
            jstring key=env->NewStringUTF(name?name:"");
            auto sample=static_cast<jdoubleArray>(env->CallObjectMethod(activity,method,key,
                use?SDL_GameControllerGetVendor(controller):0,use?SDL_GameControllerGetProduct(controller):0));
            if(!env->ExceptionCheck() && sample && env->GetArrayLength(sample)==8) {
                jdouble values[8];env->GetDoubleArrayRegion(sample,0,8,values);
                if(!env->ExceptionCheck()) {
                    motion=ThreeDsRecomp::Input::ConvertSdlMotion(
                        {float(values[0]),float(values[1]),float(values[2])},true,
                        {float(values[3]),float(values[4]),float(values[5])},true);
                    motion.AccelerometerTimestampMicroseconds=static_cast<std::uint64_t>(values[6]/1000);
                    motion.GyroscopeTimestampMicroseconds=static_cast<std::uint64_t>(values[7]/1000);
                }
            }
        }
        if(env->ExceptionCheck())env->ExceptionClear();
    }
    env->PopLocalFrame(nullptr);
}
}
#endif
