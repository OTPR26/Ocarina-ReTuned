#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>
#import <TargetConditionals.h>
#include <SDL.h>
#include "fast/oot3d/retuned_render_resolution.h"
#ifndef __IOS__
#error Apple mobile host must use the same iOS platform definition as the renderer
#endif
#include "startup_status.h"
#include "television_resolution.h"
#include "apple_paths.h"
#include <cstdio>
#include <exception>
#include <filesystem>
#include <string>
#include <vector>

int RetunedNativeMain(int argc, char** argv);
extern "C" bool RetunedSaveSyncRecoverLocal(const char* saves);
#if TARGET_OS_IOS && !TARGET_OS_TV
extern "C" void RetunedInitializeTextureFolder(const char* dataDirectory);
#endif
extern "C" float RetunedAppleScreenScale() { return static_cast<float>(UIScreen.mainScreen.nativeScale); }


static int RunPreparedAppleGame() {
    @autoreleasepool {
        NSString* bundle=NSBundle.mainBundle.bundlePath;
        const auto setup=RetunedValidateAppleSetup(bundle);
        if(setup!=RetunedAppleStartupReady)return RetunedPresentAppleStartupIssue(setup);
        SDL_setenv("SDL_VULKAN_LIBRARY",[[bundle stringByAppendingPathComponent:@"Frameworks/MoltenVK.framework/MoltenVK"] UTF8String],1);
#if TARGET_OS_TV
        SDL_SetHint(SDL_HINT_TV_REMOTE_AS_JOYSTICK,"0");
        SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");
        SDL_SetHint(SDL_HINT_APPLE_TV_CONTROLLER_UI_EVENTS,"0");
        const auto displayHeight=static_cast<uint32_t>(std::min(UIScreen.mainScreen.nativeBounds.size.width,
                                                              UIScreen.mainScreen.nativeBounds.size.height));
        const float defaultScale=RetunedFrontend::GameplayScaleForHeight(720,displayHeight ? displayHeight : 1080);
        SDL_setenv("RETUNED_DEFAULT_RENDER_SCALE",std::to_string(defaultScale).c_str(),1);
        const NSSearchPathDirectory storageDirectory=NSCachesDirectory;
#else
        const NSSearchPathDirectory storageDirectory=NSApplicationSupportDirectory;
#endif
        NSString* data=[NSSearchPathForDirectoriesInDomains(storageDirectory,NSUserDomainMask,YES).firstObject
            stringByAppendingPathComponent:@"OcarinaReTuned"];
        NSFileManager* files=NSFileManager.defaultManager;
        NSError* error=nil;
        for (NSString* folder in @[@"",@"config",@"logs",@"saves"])
            if (![files createDirectoryAtPath:[data stringByAppendingPathComponent:folder]
                withIntermediateDirectories:YES attributes:nil error:&error]) return RetunedPresentAppleStartupIssue(RetunedAppleStartupStorageError);
#if TARGET_OS_TV
        if(!RetunedSaveSyncRecoverLocal([[data stringByAppendingPathComponent:@"saves"] UTF8String]))
            return RetunedPresentAppleStartupIssue(RetunedAppleStartupStorageError);
#endif
        // Seed first-launch data without replacing existing progress or settings.
        NSString* seeds=[bundle stringByAppendingPathComponent:@"PrivateGame/InitialData"];
        NSDirectoryEnumerator* entries=[files enumeratorAtPath:seeds];
        for (NSString* relative in entries) {
            NSString* source=[seeds stringByAppendingPathComponent:relative];
            NSString* destination=[data stringByAppendingPathComponent:relative];
            BOOL directory=NO;
            [files fileExistsAtPath:source isDirectory:&directory];
            if (directory) {
                [files createDirectoryAtPath:destination withIntermediateDirectories:YES attributes:nil error:&error];
            } else if (![files fileExistsAtPath:destination]) {
                NSData* bytes=[NSData dataWithContentsOfFile:source];
                if ([relative.pathExtension isEqualToString:@"json"]) {
                    id document=[NSJSONSerialization JSONObjectWithData:bytes options:0 error:&error];
                    if (document) bytes=[NSJSONSerialization dataWithJSONObject:ResolvePaths(document,bundle,data) options:0 error:&error];
                }
                if (!bytes || ![bytes writeToFile:destination options:NSDataWritingAtomic error:&error]) return RetunedPresentAppleStartupIssue(RetunedAppleStartupStorageError);
            }
        }
        NSString* settings=[data stringByAppendingPathComponent:@"config/native-game.json"];
        NSData* existing=[NSData dataWithContentsOfFile:settings];
#if TARGET_OS_TV
        NSMutableDictionary* document=existing ?
            [NSJSONSerialization JSONObjectWithData:existing options:NSJSONReadingMutableContainers error:&error] : [NSMutableDictionary dictionary];
        if(![document isKindOfClass:NSMutableDictionary.class])return RetunedPresentAppleStartupIssue(RetunedAppleStartupStorageError);
        NSMutableDictionary* graphics=document[@"Graphics"];
        if(!graphics){graphics=[NSMutableDictionary dictionary];document[@"Graphics"]=graphics;}
        if(![graphics isKindOfClass:NSMutableDictionary.class])return RetunedPresentAppleStartupIssue(RetunedAppleStartupStorageError);
        const bool hasScale=[graphics[@"RenderScale"] isKindOfClass:NSNumber.class];
        const bool initialized=[NSUserDefaults.standardUserDefaults boolForKey:@"RetunedTV.ResolutionDefaults.v1"];
        if(!initialized || !hasScale) {
            // Migrate the old match-display default once; keep custom scales.
            if(RetunedTV::UseDefaultResolution(initialized,hasScale,[graphics[@"RenderScale"] doubleValue]))
                graphics[@"RenderScale"]=@(defaultScale);
            NSData* updated=[NSJSONSerialization dataWithJSONObject:document options:0 error:&error];
            if(!updated || ![updated writeToFile:settings options:NSDataWritingAtomic error:&error])return RetunedPresentAppleStartupIssue(RetunedAppleStartupStorageError);
            existing=updated;
            [NSUserDefaults.standardUserDefaults setBool:YES forKey:@"RetunedTV.ResolutionDefaults.v1"];
            [NSUserDefaults.standardUserDefaults synchronize];
        }
#endif
        if (existing) {
            id document=[NSJSONSerialization JSONObjectWithData:existing options:0 error:&error];
            id resolved=document ? ResolvePaths(document,bundle,data) : nil;
            if (resolved && ![resolved isEqual:document]) {
                NSData* updated=[NSJSONSerialization dataWithJSONObject:resolved options:0 error:&error];
                if (!updated || ![updated writeToFile:settings options:NSDataWritingAtomic error:&error]) return RetunedPresentAppleStartupIssue(RetunedAppleStartupStorageError);
            }
        }
#if TARGET_OS_IOS && !TARGET_OS_TV
        RetunedInitializeTextureFolder(data.UTF8String);
#endif
        SDL_setenv("RETUNED_DATA_DIRECTORY", data.UTF8String, 1);
        SDL_setenv("RETUNED_RESOURCE_DIRECTORY", [[bundle stringByAppendingPathComponent:@"PrivateGame"] UTF8String], 1);
        std::filesystem::current_path(data.UTF8String);
        std::freopen([[data stringByAppendingPathComponent:@"logs/stdout.log"] UTF8String],"w",stdout);
        std::freopen([[data stringByAppendingPathComponent:@"logs/stderr.log"] UTF8String],"w",stderr);
        std::setvbuf(stdout,nullptr,_IOLBF,0);
        NSString* privateRoot=[bundle stringByAppendingPathComponent:@"PrivateGame"];
        for (NSString* name in @[@"process-manifest.json",@"native-launch.json"]) {
            NSData* input=[NSData dataWithContentsOfFile:[privateRoot stringByAppendingPathComponent:name]];
            if (!input) return RetunedPresentAppleStartupIssue(RetunedAppleStartupInvalidSetup);
            id document=[NSJSONSerialization JSONObjectWithData:input options:0 error:&error];
            if (![document isKindOfClass:NSDictionary.class]) return RetunedPresentAppleStartupIssue(RetunedAppleStartupInvalidSetup);
            NSData* output=[NSJSONSerialization dataWithJSONObject:ResolvePaths(document,bundle,data) options:0 error:&error];
            if (!output || ![output writeToFile:[data stringByAppendingPathComponent:name] options:NSDataWritingAtomic error:&error]) return RetunedPresentAppleStartupIssue(RetunedAppleStartupStorageError);
        }
        std::string profile=[[data stringByAppendingPathComponent:@"native-launch.json"] UTF8String];
        std::vector<std::string> arguments={"OcarinaReTuned","--launch-profile",profile};
        std::vector<char*> pointers;
        for (auto& argument:arguments) pointers.push_back(argument.data());
        const int result=RetunedNativeMain(static_cast<int>(pointers.size()),pointers.data());
        return result ? RetunedPresentAppleStartupIssue(RetunedAppleStartupRuntimeError) : 0;
    }
}

int main(int, char**) {
    @autoreleasepool {
        try {
            const int result=RunPreparedAppleGame();
            return result;
        } catch(const std::exception&) {
            return RetunedPresentAppleStartupIssue(RetunedAppleStartupRuntimeError);
        } catch(...) {
            return RetunedPresentAppleStartupIssue(RetunedAppleStartupRuntimeError);
        }
    }
}
