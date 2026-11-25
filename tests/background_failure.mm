#import "../tools/native/apple/background_failure.h"
#include <cassert>
int main() { @autoreleasepool {
    NSString* root=[NSTemporaryDirectory() stringByAppendingPathComponent:NSUUID.UUID.UUIDString];
    auto files=NSFileManager.defaultManager;
    for (NSString* part in @[@"logs",@"config",@"saves"])
        assert([files createDirectoryAtPath:[root stringByAppendingPathComponent:part] withIntermediateDirectories:YES attributes:nil error:nil]);
    NSString* marker=[root stringByAppendingPathComponent:@"config/native-game.json.launching"];
    NSString* log=[root stringByAppendingPathComponent:@"logs/stderr.log"];
    NSString* config=[root stringByAppendingPathComponent:@"config/native-game.json"];
    NSString* save=[root stringByAppendingPathComponent:@"saves/save00.bin"];
    for (NSString* path in @[marker,config,save])
        assert([@"keep" writeToFile:path atomically:YES encoding:NSUTF8StringEncoding error:nil]);
    assert(!RetunedPreserveSettingsAfterBackgroundFailure(root));
    assert([@"VK_ERROR_DEVICE_LOST: unrelated graphics failure" writeToFile:log atomically:YES encoding:NSUTF8StringEncoding error:nil]);
    assert(!RetunedPreserveSettingsAfterBackgroundFailure(root));
    assert([files fileExistsAtPath:marker]);
    assert([@"VK_ERROR_DEVICE_LOST: kIOGPUCommandBufferCallbackErrorBackgroundExecutionNotPermitted" writeToFile:log atomically:YES encoding:NSUTF8StringEncoding error:nil]);
    assert(RetunedPreserveSettingsAfterBackgroundFailure(root));
    assert(![files fileExistsAtPath:marker]);
    assert(!RetunedPreserveSettingsAfterBackgroundFailure(root));
    for (NSString* path in @[config,save])
        assert([[NSString stringWithContentsOfFile:path encoding:NSUTF8StringEncoding error:nil] isEqualToString:@"keep"]);
    assert([files removeItemAtPath:root error:nil]);
} }
