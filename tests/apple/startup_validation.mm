#import <Foundation/Foundation.h>
#include "startup_status.h"
#include <cassert>
int main(){@autoreleasepool {
    NSString* root=[NSTemporaryDirectory() stringByAppendingPathComponent:NSUUID.UUID.UUIDString];
    NSFileManager* fm=NSFileManager.defaultManager;
    assert(RetunedValidateAppleSetup(root)==RetunedAppleStartupMissingGame);
    NSString* game=[root stringByAppendingPathComponent:@"PrivateGame"];
    [fm createDirectoryAtPath:game withIntermediateDirectories:YES attributes:nil error:nil];
    assert(RetunedValidateAppleSetup(root)==RetunedAppleStartupInvalidSetup);
    [@"[]" writeToFile:[game stringByAppendingPathComponent:@"process-manifest.json"] atomically:YES encoding:NSUTF8StringEncoding error:nil];
    assert(RetunedValidateAppleSetup(root)==RetunedAppleStartupInvalidSetup);
    [@"{\"source\":{}}" writeToFile:[game stringByAppendingPathComponent:@"process-manifest.json"] atomically:YES encoding:NSUTF8StringEncoding error:nil];
    [@"{\"arguments\":[true]}" writeToFile:[game stringByAppendingPathComponent:@"native-launch.json"] atomically:YES encoding:NSUTF8StringEncoding error:nil];
    assert(RetunedValidateAppleSetup(root)==RetunedAppleStartupInvalidSetup);
    [@"{\"arguments\":[\"--launch-profile\"]}" writeToFile:[game stringByAppendingPathComponent:@"native-launch.json"] atomically:YES encoding:NSUTF8StringEncoding error:nil];
    for(NSString* name in @[@"code.bin",@"exheader.bin",@"romfs.bin",@"font_coverage.zip"])
        [@"fixture" writeToFile:[game stringByAppendingPathComponent:name] atomically:YES encoding:NSUTF8StringEncoding error:nil];
    assert(RetunedValidateAppleSetup(root)==RetunedAppleStartupMissingModule);
    NSString* module=[root stringByAppendingPathComponent:@"Frameworks/triaevum_title_aot.framework/triaevum_title_aot"];
    [fm createDirectoryAtPath:module.stringByDeletingLastPathComponent withIntermediateDirectories:YES attributes:nil error:nil];
    [@"fixture" writeToFile:module atomically:YES encoding:NSUTF8StringEncoding error:nil];
    assert(RetunedValidateAppleSetup(root)==RetunedAppleStartupReady);
    NSString* save=[root stringByAppendingPathComponent:@"existing-save"];
    [@"unchanged" writeToFile:save atomically:YES encoding:NSUTF8StringEncoding error:nil];
    RetunedValidateAppleSetup(root);
    assert([[NSString stringWithContentsOfFile:save encoding:NSUTF8StringEncoding error:nil] isEqual:@"unchanged"]);
    [fm removeItemAtPath:root error:nil];puts("Apple setup validation and read-only preservation checks passed");
}}
