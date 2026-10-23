// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#ifdef __ANDROID__
#include <imgui.h>
#include <SDL.h>
#include <jni.h>
#include "fast/oot3d/retuned_frontend_state.h"
namespace RetunedFrontend {
inline void OpenAndroidSaveFiles(const char* action){
 auto* env=static_cast<JNIEnv*>(SDL_AndroidGetJNIEnv());auto activity=static_cast<jobject>(SDL_AndroidGetActivity());if(!env||!activity)return;
 auto type=env->GetObjectClass(activity);auto method=env->GetMethodID(type,"retunedOpenSaveFiles","(Ljava/lang/String;)V");auto value=env->NewStringUTF(action);
 if(method)env->CallVoidMethod(activity,method,value);
 if(env->ExceptionCheck()){env->ExceptionClear();SDL_LogError(SDL_LOG_CATEGORY_APPLICATION,"Could not open save-file manager");}
 env->DeleteLocalRef(value);env->DeleteLocalRef(type);env->DeleteLocalRef(activity);
}
inline void DrawAndroidSaveFiles(){
 ImGui::TextWrapped("Transfer ordinary Citra/Azahar game saves or select a folder for Syncthing. Save states are separate.");
 auto* env=static_cast<JNIEnv*>(SDL_AndroidGetJNIEnv());auto activity=static_cast<jobject>(SDL_AndroidGetActivity());
 if(env&&activity){
  auto type=env->GetObjectClass(activity);auto method=env->GetMethodID(type,"retunedSaveFilesStatus","()Ljava/lang/String;");
  auto value=method?static_cast<jstring>(env->CallObjectMethod(activity,method)):nullptr;
  if(env->ExceptionCheck())env->ExceptionClear();
  else if(value){const char* text=env->GetStringUTFChars(value,nullptr);if(text){if(*text)ImGui::TextWrapped("%s",text);env->ReleaseStringUTFChars(value,text);}}
  if(value)env->DeleteLocalRef(value);env->DeleteLocalRef(type);env->DeleteLocalRef(activity);
 }
 if(!StartupVisible)ImGui::TextWrapped("Save your game, then reopen the app to import saves or change the save folder before starting gameplay.");
 ImGui::BeginDisabled(!StartupVisible);
 if(ImGui::Button("Import saves"))OpenAndroidSaveFiles("import");
 if(ImGui::Button("Export saves"))OpenAndroidSaveFiles("export");
 if(ImGui::Button("Custom save folder"))OpenAndroidSaveFiles("folder");
 if(ImGui::Button("Manage save files"))OpenAndroidSaveFiles("");
 ImGui::EndDisabled();
}
}
#endif
