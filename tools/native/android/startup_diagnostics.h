#pragma once

#ifdef __ANDROID__
#include <SDL.h>
#include <jni.h>
#endif

#ifdef __ANDROID__
template <typename... Args>
inline void RetunedStartupCall(const char* name, const char* signature, Args... arguments) {
    auto* env = static_cast<JNIEnv*>(SDL_AndroidGetJNIEnv());
    auto activity = static_cast<jobject>(SDL_AndroidGetActivity());
    if (!env || !activity) return;
    if (env->ExceptionCheck()) { env->DeleteLocalRef(activity); return; }
    auto type = env->GetObjectClass(activity);
    auto method = type ? env->GetMethodID(type, name, signature) : nullptr;
    if (method) env->CallVoidMethod(activity, method, arguments...);
    // A reporting failure must not prevent startup or replace its real error.
    if (env->ExceptionCheck()) env->ExceptionClear();
    if (type) env->DeleteLocalRef(type);
    env->DeleteLocalRef(activity);
}
#endif

inline void RetunedStartupStage(int stage) {
#ifdef __ANDROID__
    RetunedStartupCall("retunedStartupStage", "(I)V", static_cast<jint>(stage));
#else
    (void)stage;
#endif
}

inline void RetunedStartupGraphics(unsigned api, unsigned vendor, unsigned driver) {
#ifdef __ANDROID__
    RetunedStartupCall("retunedStartupGraphics", "(III)V", static_cast<jint>(api),
                       static_cast<jint>(vendor), static_cast<jint>(driver));
#else
    (void)api; (void)vendor; (void)driver;
#endif
}
