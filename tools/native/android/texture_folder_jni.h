// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "fast/oot3d/retuned_texture_folder.h"
#include <SDL.h>
#include <jni.h>
namespace RetunedFrontend {
inline std::string AndroidTextureText(const char* method){
 auto* env=static_cast<JNIEnv*>(SDL_AndroidGetJNIEnv());auto activity=static_cast<jobject>(SDL_AndroidGetActivity());
 if(!env||!activity)return {};
 const auto type=env->GetObjectClass(activity);const auto id=env->GetMethodID(type,method,"()Ljava/lang/String;");
 auto value=id?static_cast<jstring>(env->CallObjectMethod(activity,id)):nullptr;std::string result;
 if(env->ExceptionCheck()){env->ExceptionClear();}else if(value){const char* text=env->GetStringUTFChars(value,nullptr);if(text){result=text;env->ReleaseStringUTFChars(value,text);}}
 if(value)env->DeleteLocalRef(value);env->DeleteLocalRef(type);env->DeleteLocalRef(activity);return result;
}
inline void InstallAndroidTextureFolder(){
 static bool installed=false;if(installed)return;installed=true;
 TextureFolders.Choose=[] {
  auto* env=static_cast<JNIEnv*>(SDL_AndroidGetJNIEnv());auto activity=static_cast<jobject>(SDL_AndroidGetActivity());if(!env||!activity)return;
  auto type=env->GetObjectClass(activity);auto id=env->GetMethodID(type,"retunedChooseTextureFolder","()V");if(id)env->CallVoidMethod(activity,id);
  if(env->ExceptionCheck())env->ExceptionClear();env->DeleteLocalRef(type);env->DeleteLocalRef(activity);
 };
 TextureFolders.Status=[]{return AndroidTextureText("retunedTextureFolderStatus");};
 TextureFolders.TakeSelection=[]{return AndroidTextureText("retunedTakeTextureFolder");};
 TextureFolders.Read=[](const std::string& path){
  auto* env=static_cast<JNIEnv*>(SDL_AndroidGetJNIEnv());auto activity=static_cast<jobject>(SDL_AndroidGetActivity());if(!env||!activity)throw std::runtime_error("Texture folder is unavailable");
  auto type=env->GetObjectClass(activity);auto id=env->GetMethodID(type,"retunedReadTextureFile","(Ljava/lang/String;)[B");auto name=env->NewStringUTF(path.c_str());
  auto data=id?static_cast<jbyteArray>(env->CallObjectMethod(activity,id,name)):nullptr;
  bool failed=env->ExceptionCheck();if(failed)env->ExceptionClear();std::vector<uint8_t> bytes;
  if(data&&!failed){const auto count=env->GetArrayLength(data);bytes.resize(count);env->GetByteArrayRegion(data,0,count,reinterpret_cast<jbyte*>(bytes.data()));}
  if(data)env->DeleteLocalRef(data);env->DeleteLocalRef(name);env->DeleteLocalRef(type);env->DeleteLocalRef(activity);
  if(bytes.empty())throw std::runtime_error("Could not read texture; choose its folder again");return bytes;
 };
}
}
