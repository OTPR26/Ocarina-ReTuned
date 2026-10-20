// SPDX-License-Identifier: GPL-2.0-or-later
#import <Foundation/Foundation.h>
#import <CloudKit/CloudKit.h>
#import <CommonCrypto/CommonDigest.h>
#import <Security/Security.h>
#include "save_sync.h"
#include "save_sync_policy.h"
#include <mutex>
#include <string>
#include <chrono>
#include <cstring>

// The signing profile must grant this exact container; unsigned builds stay offline.
#ifndef RETUNED_ICLOUD_CONTAINER
#define RETUNED_ICLOUD_CONTAINER ""
#endif
#ifndef RETUNED_ICLOUD_RECORD_ID
#define RETUNED_ICLOUD_RECORD_ID "oot3d-usa-saves-v1"
#endif
namespace {
std::mutex lock;
NSString* root=nil;
NSString* status=@"iCloud sync is unavailable in this signing configuration.";
NSData* pending=nil;
NSData* latestLocal=nil;
NSString* pendingExpected=nil;
CKRecord* conflictRecord=nil;
NSString* account=nil;
NSString* baselineKey=nil;
bool enabled=true, busy=false, conflict=false, request=true;
bool forceLocal=false;
NSString* forceRemoteDigest=nil;
uint64_t generation=0;
auto next=std::chrono::steady_clock::time_point{};
dispatch_queue_t Queue() {
 static dispatch_queue_t q=dispatch_queue_create("io.github.otpr26.ocarinaretuned.save-sync",DISPATCH_QUEUE_SERIAL);
 return q;
}
NSString* Hash(NSData* data) {
 if(!data.length)return @"";
 unsigned char bytes[CC_SHA256_DIGEST_LENGTH];
 CC_SHA256(data.bytes,(CC_LONG)data.length,bytes);
 NSMutableString* result=[NSMutableString string];
 for(auto value:bytes)[result appendFormat:@"%02x",value];
 return result;
}
std::string Text(NSString* value) {return value ? std::string(value.UTF8String) : std::string();}
NSArray<NSString*>* Names() {
 return @[@"save00.bin",@"save01.bin",@"save02.bin",@"save03.bin",@"save04.bin",@"save05.bin",@"system.dat"];
}
bool Regular(NSString* path) {
 NSDictionary* attrs=[NSFileManager.defaultManager attributesOfItemAtPath:path error:nil];
 return [attrs[NSFileType] isEqual:NSFileTypeRegular];
}
NSData* Snapshot(NSString* directory) {
 if(![[NSFileManager.defaultManager attributesOfItemAtPath:directory error:nil][NSFileType] isEqual:NSFileTypeDirectory])return nil;
 NSMutableDictionary* files=[NSMutableDictionary dictionary];
 for(NSString* name in Names()) {
  NSString* path=[directory stringByAppendingPathComponent:name];
  if(![NSFileManager.defaultManager fileExistsAtPath:path])continue;
  if(!Regular(path))return nil;
  NSData* bytes=[NSData dataWithContentsOfFile:path];
  const NSUInteger expected=[name isEqualToString:@"system.dat"] ? 34 : 5340;
  if(bytes.length!=expected)return nil;
  files[name]=[bytes base64EncodedStringWithOptions:0];
 }
 if(!files.count)return [NSData data];
 return [NSJSONSerialization dataWithJSONObject:@{@"version":@1,@"files":files} options:NSJSONWritingSortedKeys error:nil];
}
NSDictionary* Validate(NSData* bytes) {
 if(!bytes.length || bytes.length>128*1024)return nil;
 id document=[NSJSONSerialization JSONObjectWithData:bytes options:0 error:nil];
 if(![document isKindOfClass:NSDictionary.class] || ![document[@"version"] isEqual:@1])return nil;
 id files=document[@"files"];
 if(![files isKindOfClass:NSDictionary.class] || ![files count] || [files count]>7)return nil;
 NSMutableDictionary* result=[NSMutableDictionary dictionary];
 for(id name in files) {
  if(![name isKindOfClass:NSString.class] || !RetunedSaveSync::SaveName(Text(name)) || ![files[name] isKindOfClass:NSString.class])return nil;
  NSData* value=[[NSData alloc] initWithBase64EncodedString:files[name] options:0];
  if(value.length!=([name isEqualToString:@"system.dat"] ? 34 : 5340))return nil;
  result[name]=value;
 }
 return result;
}
bool Restore(NSData* bytes) {
 NSDictionary* files=Validate(bytes);
 if(!files)return false;
 NSFileManager* fm=NSFileManager.defaultManager;
 NSString* parent=root.stringByDeletingLastPathComponent;
 NSString* token=NSUUID.UUID.UUIDString;
 NSString* stage=[parent stringByAppendingPathComponent:[@".sync-stage-" stringByAppendingString:token]];
 NSString* backup=[parent stringByAppendingPathComponent:[@"save-backup-" stringByAppendingString:token]];
 if([fm fileExistsAtPath:root]) {
  if(![fm copyItemAtPath:root toPath:stage error:nil])return false;
 } else if(![fm createDirectoryAtPath:stage withIntermediateDirectories:YES attributes:nil error:nil])return false;
 bool ok=true;
 for(NSString* name in files) {
  NSString* path=[stage stringByAppendingPathComponent:name];
  if([fm fileExistsAtPath:path] && !Regular(path)){ok=false;break;}
  if(![files[name] writeToFile:path options:NSDataWritingAtomic error:nil]){ok=false;break;}
 }
 if(ok && [fm fileExistsAtPath:root])ok=[fm moveItemAtPath:root toPath:backup error:nil];
 if(ok && ![fm moveItemAtPath:stage toPath:root error:nil]) {
  if([fm fileExistsAtPath:backup])[fm moveItemAtPath:backup toPath:root error:nil];
  ok=false;
 }
 [fm removeItemAtPath:stage error:nil];
 return ok;
}
void Finish(NSString* message, uint64_t version) {
 std::scoped_lock guard(lock);
 if(version!=generation)return;
 status=message;busy=false;
}
void Sync(NSData* local, bool overwrite, NSString* expectedRemote, uint64_t version) {
 @autoreleasepool {
  NSString* containerID=@RETUNED_ICLOUD_CONTAINER;
  if(!containerID.length){Finish(@"iCloud requires a signed build with an enabled CloudKit container.",version);return;}
  @try {
   CKContainer* container=[CKContainer containerWithIdentifier:containerID];
   [container accountStatusWithCompletionHandler:^(CKAccountStatus available,NSError* error){
    dispatch_async(Queue(),^{
     if(available!=CKAccountStatusAvailable){Finish(@"Sign in to iCloud to sync. Local saves are available.",version);return;}
     [container fetchUserRecordIDWithCompletionHandler:^(CKRecordID* user,NSError* userError){
      dispatch_async(Queue(),^{
       if(!user || userError){Finish(@"Could not check iCloud account. Local saves are unchanged.",version);return;}
       NSString* userID=user.recordName;
       NSString* scope=[NSString stringWithFormat:@"%@/%@/%@",containerID,@RETUNED_ICLOUD_RECORD_ID,userID];
       NSString* key=[@"RetunedSaveSync.Base." stringByAppendingString:Hash([scope dataUsingEncoding:NSUTF8StringEncoding])];
       {
        std::scoped_lock guard(lock);
        if(version!=generation || !enabled)return;
        // An explicit conflict resolution cannot carry into another Apple account.
        if(overwrite && ![account isEqualToString:userID]){busy=false;status=@"iCloud account changed. Check saves again.";return;}
        account=userID;baselineKey=key;
       }
       CKDatabase* db=container.privateCloudDatabase;
       CKRecordID* recordID=[[CKRecordID alloc] initWithRecordName:@RETUNED_ICLOUD_RECORD_ID];
       [db fetchRecordWithID:recordID completionHandler:^(CKRecord* record,NSError* fetchError){
        dispatch_async(Queue(),^{
         {std::scoped_lock guard(lock);if(version!=generation || !enabled)return;}
         if(fetchError && fetchError.code!=CKErrorUnknownItem){Finish(@"iCloud unavailable. Your local saves remain available.",version);return;}
         NSData* remote=record[@"contents"];
         if(record && (![remote isKindOfClass:NSData.class] || !Validate(remote) || ![record[@"digest"] isEqualToString:Hash(remote)])) {
          Finish(@"Cloud save validation failed. Local saves are unchanged.",version);return;
         }
         NSString* base=[NSUserDefaults.standardUserDefaults stringForKey:key] ?: @"";
         auto action=RetunedSaveSync::Decide(Text(Hash(local)),Text(Hash(remote)),Text(base));
         if(overwrite && local.length) {
          action=[Hash(remote) isEqualToString:expectedRemote] ? RetunedSaveSync::Action::Upload : RetunedSaveSync::Action::Conflict;
         }
         if(action==RetunedSaveSync::Action::None){
          [NSUserDefaults.standardUserDefaults setObject:Hash(local) forKey:key];
          Finish(@"Saves are up to date.",version);return;
         }
         if(action==RetunedSaveSync::Action::Download || action==RetunedSaveSync::Action::Conflict){
          std::scoped_lock guard(lock);
          if(version!=generation)return;
          pending=remote;pendingExpected=Hash(local);conflictRecord=record;
          conflict=action==RetunedSaveSync::Action::Conflict;busy=false;
          status=conflict ? @"Both devices have different progress. Choose which saves to use at startup." : @"Cloud saves ready. They will be restored before starting the game.";
          return;
         }
         CKRecord* target=record ?: [[CKRecord alloc] initWithRecordType:@"ReTunedSaveBundle" recordID:recordID];
         target[@"contents"]=local;target[@"digest"]=Hash(local);target[@"schema"]=@1;
         CKModifyRecordsOperation* operation=[[CKModifyRecordsOperation alloc] initWithRecordsToSave:@[target] recordIDsToDelete:nil];
         operation.savePolicy=CKRecordSaveIfServerRecordUnchanged;
         operation.modifyRecordsCompletionBlock=^(NSArray*,NSArray*,NSError* saveError){
          dispatch_async(Queue(),^{
           {std::scoped_lock guard(lock);if(version!=generation)return;}
           if(saveError){Finish(@"Cloud save changed or upload failed. No progress was overwritten; sync again.",version);return;}
           [NSUserDefaults.standardUserDefaults setObject:Hash(local) forKey:key];
           Finish(@"Saves uploaded to iCloud.",version);
          });
         };
         [db addOperation:operation];
        });
       }];
      });
     }];
    });
   }];
  } @catch(NSException*) {Finish(@"iCloud is unavailable in this signing configuration. Local saves are available.",version);}
 }
}
}
extern "C" void RetunedSaveSyncConfigure(const char* saves) {
 static dispatch_once_t observerOnce;
 dispatch_once(&observerOnce,^{
  [NSNotificationCenter.defaultCenter addObserverForName:CKAccountChangedNotification object:nil queue:nil usingBlock:^(NSNotification*){
   std::scoped_lock guard(lock);
   generation++;busy=false;pending=nil;conflictRecord=nil;conflict=false;forceLocal=false;
   account=nil;baselineKey=nil;request=true;status=@"iCloud account changed; checking saves again.";
  }];
 });
 std::scoped_lock guard(lock);
 root=[NSString stringWithUTF8String:saves];
 enabled=![NSUserDefaults.standardUserDefaults boolForKey:@"RetunedSaveSync.Disabled"];
 generation++;busy=false;pending=nil;conflict=false;request=true;next={};latestLocal=Snapshot(root);
}
extern "C" void RetunedSaveSyncTick(bool startup) {
 std::scoped_lock guard(lock);
 if(!root || !enabled || !std::strlen(RETUNED_ICLOUD_CONTAINER))return;
 if(startup && pending && !conflict) {
  NSData* current=Snapshot(root);
  if(!current || ![Hash(current) isEqualToString:pendingExpected]) {
   conflict=true;status=@"Local progress changed while checking iCloud. Choose saves at startup.";return;
  }
  if(Restore(pending)) {
   if(baselineKey)[NSUserDefaults.standardUserDefaults setObject:Hash(pending) forKey:baselineKey];
   status=@"Cloud saves restored. Previous local saves were backed up.";
   latestLocal=Snapshot(root);pending=nil;conflictRecord=nil;
  } else status=@"Could not restore cloud saves. Local saves are unchanged.";
 }
 if(busy || pending || conflict)return;
 auto now=std::chrono::steady_clock::now();
 if(!request && now<next)return;
 next=now+std::chrono::seconds(15);request=false;
 NSData* local=startup ? Snapshot(root) : latestLocal;
 if(!local){status=@"Waiting for a complete local save before syncing.";return;}
 latestLocal=local;busy=true;status=@"Checking iCloud saves…";
 bool overwrite=forceLocal;NSString* expectedRemote=forceRemoteDigest;forceLocal=false;uint64_t version=generation;
 dispatch_async(Queue(),^{Sync(local,overwrite,expectedRemote,version);});
}
extern "C" void RetunedSaveSyncCommitted() {
 std::scoped_lock guard(lock);
 if(root) {NSData* saved=Snapshot(root);if(saved){latestLocal=saved;request=true;}}
}
extern "C" void RetunedSaveSyncRequest(){std::scoped_lock guard(lock);request=true;}
extern "C" bool RetunedSaveSyncEnabled(){std::scoped_lock guard(lock);return enabled;}
extern "C" void RetunedSaveSyncSetEnabled(bool value){
 std::scoped_lock guard(lock);enabled=value;generation++;busy=false;pending=nil;conflictRecord=nil;conflict=false;request=true;
 [NSUserDefaults.standardUserDefaults setBool:!value forKey:@"RetunedSaveSync.Disabled"];
}
extern "C" void RetunedSaveSyncStatus(char* text,unsigned long size){std::scoped_lock guard(lock);if(size)snprintf(text,size,"%s",status.UTF8String);}
extern "C" bool RetunedSaveSyncConflict(){std::scoped_lock guard(lock);return conflict;}
extern "C" void RetunedSaveSyncResolve(bool useCloud){
 std::scoped_lock guard(lock);
 if(!conflict)return;
 conflict=false;
 if(useCloud){pendingExpected=Hash(Snapshot(root));status=@"Cloud saves will be restored before starting the game.";}
 else {
  // Preserve the competing cloud copy locally before choosing this device.
  NSString* backup=[root.stringByDeletingLastPathComponent stringByAppendingPathComponent:[@"cloud-conflict-" stringByAppendingString:NSUUID.UUID.UUIDString]];
  if(![pending writeToFile:backup options:NSDataWritingAtomic error:nil]){conflict=true;status=@"Could not back up competing cloud saves. Nothing changed.";return;}
  forceRemoteDigest=Hash(pending);pending=nil;conflictRecord=nil;forceLocal=true;request=true;status=@"Keeping this device's saves; preparing upload.";}
}
