#pragma once
#if defined(__ANDROID__)
#include "document_transfer.h"
#include <SDL_system.h>
#include <jni.h>
#include <nlohmann/json.hpp>

namespace RetunedRandomizer {
class AndroidDocuments {
public:
    AndroidDocuments(RetunedFrontend::RandomizerMenuState& menu,std::function<bool()> startup)
      :transfer_(menu,std::move(startup),Begin,Take) {}
    void Poll(){transfer_.Poll();}
private:
    struct Activity {
        JNIEnv* env=static_cast<JNIEnv*>(SDL_AndroidGetJNIEnv());
        jobject object=nullptr;
        jclass type=nullptr;
        bool frame=false;
        Activity() {
            if(env && env->PushLocalFrame(12)==0) {
                frame=true;object=static_cast<jobject>(SDL_AndroidGetActivity());
                if(object)type=env->GetObjectClass(object);
            }
        }
        ~Activity(){if(env && env->ExceptionCheck())env->ExceptionClear();if(frame)env->PopLocalFrame(nullptr);}
        void Check(){if(!type || env->ExceptionCheck())throw std::runtime_error("Android document service unavailable");}
        jmethodID Method(const char* name,const char* signature) {
            Check();auto method=env->GetMethodID(type,name,signature);Check();
            if(!method)throw std::runtime_error("Android document service unavailable");
            return method;
        }
    };
    static bool Begin(unsigned slot,bool exporting,const std::string& bytes) {
        Activity activity;
        auto method=activity.Method(exporting?"retunedExportRun":"retunedImportRun",exporting?"(I[B)Z":"(I)Z");
        jboolean accepted;
        if(exporting) {
            auto data=activity.env->NewByteArray(static_cast<jsize>(bytes.size()));
            activity.Check();if(!data)throw std::runtime_error("Could not allocate export document");
            activity.env->SetByteArrayRegion(data,0,static_cast<jsize>(bytes.size()),reinterpret_cast<const jbyte*>(bytes.data()));
            activity.Check();accepted=activity.env->CallBooleanMethod(activity.object,method,static_cast<jint>(slot),data);
        } else accepted=activity.env->CallBooleanMethod(activity.object,method,static_cast<jint>(slot));
        activity.Check();return accepted==JNI_TRUE;
    }
    static std::optional<DocumentResult> Take() {
        Activity activity;
        auto method=activity.Method("retunedTakeRunDocument","()Ljava/lang/String;");
        auto value=static_cast<jstring>(activity.env->CallObjectMethod(activity.object,method));
        activity.Check();if(!value)return {};
        const auto length=activity.env->GetStringUTFLength(value);
        if(length==0)return {};
        if(length>14*1024*1024)throw std::runtime_error("Randomizer document response is too large");
        const char* chars=activity.env->GetStringUTFChars(value,nullptr);
        activity.Check();if(!chars)throw std::runtime_error("Could not read document response");
        std::string text;
        try{text.assign(chars,length);}catch(...){activity.env->ReleaseStringUTFChars(value,chars);throw;}
        activity.env->ReleaseStringUTFChars(value,chars);
        const auto json=nlohmann::json::parse(text);
        const auto operation=json.at("operation").get<std::string>();
        if(operation!="import" && operation!="export")throw std::runtime_error("Invalid document operation");
        const int slot=json.at("slot").get<int>();
        if(slot<0 || slot>2)throw std::runtime_error("Invalid document slot");
        DocumentResult result{static_cast<unsigned>(slot),operation=="export",json.at("cancelled").get<bool>(),{},json.value("error",std::string{})};
        if(json.contains("data")) {
            // Decode in Java to retain exact UTF-8 document bytes across JNI.
            const auto encoded=json.at("data").get<std::string>();
            auto decoder=activity.env->FindClass("android/util/Base64");activity.Check();
            if(!decoder)throw std::runtime_error("Document decoder unavailable");
            auto decode=activity.env->GetStaticMethodID(decoder,"decode","(Ljava/lang/String;I)[B");activity.Check();
            if(!decode)throw std::runtime_error("Document decoder unavailable");
            auto input=activity.env->NewStringUTF(encoded.c_str());activity.Check();
            if(!input)throw std::runtime_error("Could not read document bytes");
            auto bytes=static_cast<jbyteArray>(activity.env->CallStaticObjectMethod(decoder,decode,input,0));activity.Check();
            if(!bytes)throw std::runtime_error("Could not decode document bytes");
            const auto size=activity.env->GetArrayLength(bytes);
            if(size<=0 || size>DocumentTransfer::Limit)throw std::runtime_error("Invalid randomizer document size");
            result.bytes.resize(size);
            activity.env->GetByteArrayRegion(bytes,0,size,reinterpret_cast<jbyte*>(result.bytes.data()));activity.Check();
        }
        return result;
    }
    DocumentTransfer transfer_;
};
}
#endif
