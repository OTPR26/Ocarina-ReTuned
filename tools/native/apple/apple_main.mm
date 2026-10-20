#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>
#import <TargetConditionals.h>
#include <SDL.h>
#ifndef __IOS__
#error Apple mobile host must use the same iOS platform definition as the renderer
#endif
#include <cstdio>
#include <filesystem>
#include <string>
#include <vector>

int RetunedNativeMain(int argc, char** argv);
extern "C" float RetunedAppleScreenScale() { return static_cast<float>(UIScreen.mainScreen.nativeScale); }

static id ResolvePaths(id value, NSString* bundle, NSString* data) {
    if ([value isKindOfClass:NSString.class]) {
        NSString* resolved=[[value stringByReplacingOccurrencesOfString:@"@BUNDLE@" withString:bundle]
                       stringByReplacingOccurrencesOfString:@"@DATA@" withString:data];
        // Installation changes the bundle UUID; keep bundled resource references current.
        NSRange previous=[resolved rangeOfString:@"/OcarinaReTuned.app/" options:NSBackwardsSearch];
        if (previous.location != NSNotFound)
            return [bundle stringByAppendingPathComponent:[resolved substringFromIndex:NSMaxRange(previous)]];
        return resolved;
    }
    if ([value isKindOfClass:NSDictionary.class]) {
        NSMutableDictionary* result=[NSMutableDictionary dictionary];
        for (id key in value) result[key]=ResolvePaths(value[key],bundle,data);
        return result;
    }
    if ([value isKindOfClass:NSArray.class]) {
        NSMutableArray* result=[NSMutableArray array];
        for (id item in value) [result addObject:ResolvePaths(item,bundle,data)];
        return result;
    }
    return value;
}

int main(int, char**) {
    @autoreleasepool {
        NSString* bundle=NSBundle.mainBundle.bundlePath;
        SDL_setenv("SDL_VULKAN_LIBRARY",[[bundle stringByAppendingPathComponent:@"Frameworks/MoltenVK.framework/MoltenVK"] UTF8String],1);
#if TARGET_OS_TV
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
                withIntermediateDirectories:YES attributes:nil error:&error]) return 1;
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
                if (!bytes || ![bytes writeToFile:destination options:NSDataWritingAtomic error:&error]) return 1;
            }
        }
        NSString* settings=[data stringByAppendingPathComponent:@"config/native-game.json"];
        NSData* existing=[NSData dataWithContentsOfFile:settings];
        if (existing) {
            id document=[NSJSONSerialization JSONObjectWithData:existing options:0 error:&error];
            id resolved=document ? ResolvePaths(document,bundle,data) : nil;
            if (resolved && ![resolved isEqual:document]) {
                NSData* updated=[NSJSONSerialization dataWithJSONObject:resolved options:0 error:&error];
                if (!updated || ![updated writeToFile:settings options:NSDataWritingAtomic error:&error]) return 1;
            }
        }
        SDL_setenv("RETUNED_DATA_DIRECTORY", data.UTF8String, 1);
        SDL_setenv("RETUNED_RESOURCE_DIRECTORY", [[bundle stringByAppendingPathComponent:@"PrivateGame"] UTF8String], 1);
        std::filesystem::current_path(data.UTF8String);
        std::freopen([[data stringByAppendingPathComponent:@"logs/stdout.log"] UTF8String],"w",stdout);
        std::freopen([[data stringByAppendingPathComponent:@"logs/stderr.log"] UTF8String],"w",stderr);
        std::setvbuf(stdout,nullptr,_IOLBF,0);
        NSString* privateRoot=[bundle stringByAppendingPathComponent:@"PrivateGame"];
        for (NSString* name in @[@"process-manifest.json",@"native-launch.json"]) {
            NSData* input=[NSData dataWithContentsOfFile:[privateRoot stringByAppendingPathComponent:name]];
            if (!input) { std::fprintf(stderr,"Private game setup is missing.\n"); return 1; }
            id document=[NSJSONSerialization JSONObjectWithData:input options:0 error:&error];
            if (!document) return 1;
            NSData* output=[NSJSONSerialization dataWithJSONObject:ResolvePaths(document,bundle,data) options:0 error:&error];
            if (!output || ![output writeToFile:[data stringByAppendingPathComponent:name] options:NSDataWritingAtomic error:&error]) return 1;
        }
        std::string profile=[[data stringByAppendingPathComponent:@"native-launch.json"] UTF8String];
        std::vector<std::string> arguments={"OcarinaReTuned","--launch-profile",profile};
        std::vector<char*> pointers;
        for (auto& argument:arguments) pointers.push_back(argument.data());
        return RetunedNativeMain(static_cast<int>(pointers.size()),pointers.data());
    }
}
