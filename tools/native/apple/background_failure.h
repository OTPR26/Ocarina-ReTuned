// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#import <Foundation/Foundation.h>

// A denied background submission is a lifecycle failure, not evidence that
// the user's resolution/AA settings are unsafe. Preserve those settings on
// the following launch; leave the ordinary crash-loop safeguard intact.
static bool RetunedPreserveSettingsAfterBackgroundFailure(NSString* data) {
    NSString* log=[data stringByAppendingPathComponent:@"logs/stderr.log"];
    NSString* previous=[NSString stringWithContentsOfFile:log encoding:NSUTF8StringEncoding error:nil];
    if (![previous containsString:@"kIOGPUCommandBufferCallbackErrorBackgroundExecutionNotPermitted"])
        return false;
    NSString* marker=[data stringByAppendingPathComponent:@"config/native-game.json.launching"];
    return [NSFileManager.defaultManager removeItemAtPath:marker error:nil];
}
