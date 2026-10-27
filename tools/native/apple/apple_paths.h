// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#import <Foundation/Foundation.h>

static id ResolvePaths(id value, NSString* bundle, NSString* data) {
    if ([value isKindOfClass:NSString.class]) {
        NSString* resolved=[[value stringByReplacingOccurrencesOfString:@"@BUNDLE@" withString:bundle]
                       stringByReplacingOccurrencesOfString:@"@DATA@" withString:data];
        // Installation changes the bundle UUID; keep bundled resource references current.
        NSRange previous=[resolved rangeOfString:@"/OcarinaReTuned.app/" options:NSBackwardsSearch];
        if (previous.location != NSNotFound)
            return [bundle stringByAppendingPathComponent:[resolved substringFromIndex:NSMaxRange(previous)]];
        if ([resolved containsString:@"/Containers/Data/Application/"]) {
            for (NSString* marker in @[@"/Library/Caches/OcarinaReTuned", @"/Library/Application Support/OcarinaReTuned"]) {
                NSRange previousData=[resolved rangeOfString:marker options:NSBackwardsSearch];
                if (previousData.location == NSNotFound) continue;
                NSString* suffix=[resolved substringFromIndex:NSMaxRange(previousData)];
                if (!suffix.length) return data;
                if ([suffix hasPrefix:@"/"]) return [data stringByAppendingString:suffix];
            }
        }
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
