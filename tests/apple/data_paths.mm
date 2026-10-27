// SPDX-License-Identifier: GPL-2.0-or-later
#import "../../tools/native/apple/apple_paths.h"
#include <cassert>
int main() { @autoreleasepool {
 NSString* bundle=@"/new/OcarinaReTuned.app";
 NSString* data=@"/var/mobile/Containers/Data/Application/NEW/Library/Caches/OcarinaReTuned";
 NSString* old=@"/var/mobile/Containers/Data/Application/OLD/Library/Caches/OcarinaReTuned/textures/pack";
 NSString* expected=[data stringByAppendingString:@"/textures/pack"];
 assert([ResolvePaths(old,bundle,data) isEqual:expected]);
 assert([ResolvePaths([@"/private" stringByAppendingString:old],bundle,data) isEqual:expected]);
 assert([ResolvePaths(@"@DATA@/textures/pack",bundle,data) isEqual:expected]);
 assert([ResolvePaths(@"/old/OcarinaReTuned.app/PrivateGame/game",bundle,data)
         isEqual:@"/new/OcarinaReTuned.app/PrivateGame/game"]);
 NSString* external=@"/var/mobile/Containers/Shared/AppGroup/OTHER/pack";
 assert([ResolvePaths(external,bundle,data) isEqual:external]);
 NSDictionary* result=ResolvePaths(@{@"Graphics":@{@"paths":@[old,external]}},bundle,data);
 assert([result[@"Graphics"][@"paths"][0] isEqual:expected]);
 assert([result[@"Graphics"][@"paths"][1] isEqual:external]);
 NSString* ios=@"/var/mobile/Containers/Data/Application/OLD/Library/Application Support/OcarinaReTuned/textures/pack";
 assert([ResolvePaths(ios,bundle,data) isEqual:expected]);
 NSString* other=@"/var/mobile/Containers/Data/Application/OLD/Library/Caches/OcarinaReTunedOther/pack";
 assert([ResolvePaths(other,bundle,data) isEqual:other]);
 }}
