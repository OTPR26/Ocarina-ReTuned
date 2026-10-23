// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#import <Foundation/Foundation.h>

typedef NS_ENUM(NSInteger, RetunedAppleStartupIssue) {
    RetunedAppleStartupReady = 0,
    RetunedAppleStartupMissingGame,
    RetunedAppleStartupInvalidSetup,
    RetunedAppleStartupMissingModule,
    RetunedAppleStartupStorageError,
    RetunedAppleStartupRuntimeError,
};

// Read-only preflight. Never writes to the app's saves or settings.
static inline RetunedAppleStartupIssue RetunedValidateAppleSetup(NSString* bundle) {
    NSFileManager* files=NSFileManager.defaultManager;
    NSString* root=[bundle stringByAppendingPathComponent:@"PrivateGame"];
    if (![files fileExistsAtPath:root]) return RetunedAppleStartupMissingGame;
    for (NSString* name in @[@"process-manifest.json",@"native-launch.json"]) {
        NSData* bytes=[NSData dataWithContentsOfFile:[root stringByAppendingPathComponent:name]];
        if (!bytes.length) return RetunedAppleStartupInvalidSetup;
        id document=[NSJSONSerialization JSONObjectWithData:bytes options:0 error:nil];
        if (![document isKindOfClass:NSDictionary.class]) return RetunedAppleStartupInvalidSetup;
        if ([name isEqualToString:@"native-launch.json"]) {
            id arguments=document[@"arguments"];
            if (![arguments isKindOfClass:NSArray.class] || ![arguments count]) return RetunedAppleStartupInvalidSetup;
            for (id argument in arguments) if (![argument isKindOfClass:NSString.class]) return RetunedAppleStartupInvalidSetup;
        } else if (![document[@"source"] isKindOfClass:NSDictionary.class]) return RetunedAppleStartupInvalidSetup;
    }
    for (NSString* name in @[@"code.bin",@"exheader.bin",@"romfs.bin",@"font_coverage.zip"]) {
        NSDictionary* attrs=[files attributesOfItemAtPath:[root stringByAppendingPathComponent:name] error:nil];
        if (![attrs[NSFileType] isEqual:NSFileTypeRegular] || [attrs[NSFileSize] unsignedLongLongValue]==0)
            return RetunedAppleStartupInvalidSetup;
    }
    NSString* module=[bundle stringByAppendingPathComponent:@"Frameworks/triaevum_title_aot.framework/triaevum_title_aot"];
    NSDictionary* attrs=[files attributesOfItemAtPath:module error:nil];
    if (![attrs[NSFileType] isEqual:NSFileTypeRegular] || [attrs[NSFileSize] unsignedLongLongValue]==0)
        return RetunedAppleStartupMissingModule;
    return RetunedAppleStartupReady;
}

// The SDL UIKit lifecycle keeps running after main returns, retaining this UI.
int RetunedPresentAppleStartupIssue(RetunedAppleStartupIssue issue);
