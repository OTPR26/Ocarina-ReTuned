// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#if defined(__APPLE__)
extern "C" {
void RetunedSaveSyncConfigure(const char* saves);
void RetunedSaveSyncTick(bool startup);
void RetunedSaveSyncRequest();
void RetunedSaveSyncCommitted();
bool RetunedSaveSyncEnabled();
void RetunedSaveSyncSetEnabled(bool enabled);
void RetunedSaveSyncStatus(char* text, unsigned long size);
bool RetunedSaveSyncConflict();
void RetunedSaveSyncResolve(bool useCloud);
}
#elif defined(__ANDROID__)
#include <SDL.h>
#include <jni.h>
inline void RetunedSaveSyncConfigure(const char*) {}
inline void RetunedSaveSyncTick(bool) {}
inline void RetunedSaveSyncCommitted() {
 auto* env=static_cast<JNIEnv*>(SDL_AndroidGetJNIEnv());auto activity=static_cast<jobject>(SDL_AndroidGetActivity());if(!env||!activity)return;
 auto type=env->GetObjectClass(activity);auto method=env->GetMethodID(type,"retunedSaveCommitted","()V");if(method)env->CallVoidMethod(activity,method);
 if(env->ExceptionCheck()){env->ExceptionClear();SDL_LogError(SDL_LOG_CATEGORY_APPLICATION,"Save-folder sync could not capture the committed save");}
 env->DeleteLocalRef(type);env->DeleteLocalRef(activity);
}
#else
inline void RetunedSaveSyncConfigure(const char*) {}
inline void RetunedSaveSyncTick(bool) {}
inline void RetunedSaveSyncCommitted() {}
#endif
