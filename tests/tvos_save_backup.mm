// SPDX-License-Identifier: GPL-2.0-or-later
#define RETUNED_TV_SAVE_BACKUP_TEST 1
#import "../tools/native/apple/save_sync.mm"
#include <cassert>
int main() { @autoreleasepool {
 NSFileManager* fm=NSFileManager.defaultManager;
 NSString* domain=[@"io.github.otpr26.ocarinaretuned.test." stringByAppendingString:NSUUID.UUID.UUIDString];
 NSUserDefaults* defaults=[[NSUserDefaults alloc] initWithSuiteName:domain];
 NSString* temp=[NSTemporaryDirectory() stringByAppendingPathComponent:NSUUID.UUID.UUIDString];
 NSString* saves=[temp stringByAppendingPathComponent:@"saves"];
 assert([fm createDirectoryAtPath:saves withIntermediateDirectories:YES attributes:nil error:nil]);
 for(NSString* name in Names()) {
  NSMutableData* value=[NSMutableData dataWithLength:[name isEqualToString:@"system.dat"]?34:5340];
  memset(value.mutableBytes,0x41,value.length);
  assert([value writeToFile:[saves stringByAppendingPathComponent:name] atomically:YES]);
 }
 NSData* original=Snapshot(saves);
 assert(StoreTVBackup(defaults,domain,original));
 assert([fm removeItemAtPath:saves error:nil]);
 defaults=[[NSUserDefaults alloc] initWithSuiteName:domain];
 assert(RestoreTVBackup(defaults,saves));
 assert([Snapshot(saves) isEqual:original]);
 NSString* first=[saves stringByAppendingPathComponent:@"save00.bin"];
 NSMutableData* newer=[NSMutableData dataWithLength:5340];memset(newer.mutableBytes,0x42,newer.length);
 assert([newer writeToFile:first atomically:YES]);
 assert([fm removeItemAtPath:[saves stringByAppendingPathComponent:@"save01.bin"] error:nil]);
 assert(RestoreTVBackup(defaults,saves));
 assert([[NSData dataWithContentsOfFile:first] isEqual:newer]);
 assert(Validate(Snapshot(saves)).count==7);
 NSData* updated=Snapshot(saves);assert(StoreTVBackup(defaults,domain,updated));
 assert(!StoreTVBackup(defaults,domain,[NSData data]));
 assert([fm removeItemAtPath:saves error:nil]);assert(RestoreTVBackup(defaults,saves));
 assert([Snapshot(saves) isEqual:updated]);
 [defaults setObject:[NSMutableData dataWithLength:390*1024] forKey:@"unrelated"];
 assert(!StoreTVBackup(defaults,domain,original));
 assert([fm removeItemAtPath:saves error:nil]);assert(RestoreTVBackup(defaults,saves));
 assert([Snapshot(saves) isEqual:updated]);
 [defaults removeObjectForKey:@"unrelated"];
 [defaults setObject:[@"corrupt" dataUsingEncoding:NSUTF8StringEncoding] forKey:TVBackupKey];
 assert(RestoreTVBackup(defaults,saves));
 assert([Snapshot(saves) isEqual:updated]);
 [defaults removeObjectForKey:TVBackupKey];
 assert(StoreTVBackup(defaults,domain,updated));
 assert([fm removeItemAtPath:[saves stringByAppendingPathComponent:@"save01.bin"] error:nil]);
 assert(StoreTVBackup(defaults,domain,Snapshot(saves)));
 assert([fm removeItemAtPath:saves error:nil]);assert(RestoreTVBackup(defaults,saves));
 assert([Snapshot(saves) isEqual:updated]);
 assert([fm removeItemAtPath:first error:nil]);
 assert([fm createSymbolicLinkAtPath:first withDestinationPath:@"/dev/null" error:nil]);
 assert(!RestoreTVBackup(defaults,saves));
 assert([fm removeItemAtPath:saves error:nil]);
 [defaults setObject:[@"corrupt" dataUsingEncoding:NSUTF8StringEncoding] forKey:TVBackupKey];
 assert(!RestoreTVBackup(defaults,saves));
 assert(![fm fileExistsAtPath:saves]);
 [defaults removePersistentDomainForName:domain];[defaults synchronize];
 [fm removeItemAtPath:temp error:nil];
 }}
