// SPDX-License-Identifier: GPL-2.0-or-later
#import <UIKit/UIKit.h>
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>
#include "fast/oot3d/retuned_texture_folder.h"
#include <mutex>
namespace {
std::mutex FolderMutex;
std::string FolderSelection,FolderStatus;
NSMutableArray<NSURL*>* OpenFolders;
void Status(NSString* text){std::lock_guard lock(FolderMutex);FolderStatus=text.UTF8String?:"";}
void Select(NSURL* url){std::lock_guard lock(FolderMutex);FolderSelection=url.path.UTF8String;FolderStatus="Texture folder selected. Source files stay in Files.";}
void UpdateConfig(NSString* data,NSURL* url){
 NSString* path=[data stringByAppendingPathComponent:@"config/native-game.json"];
 NSData* bytes=[NSData dataWithContentsOfFile:path];if(!bytes)return;
 NSError* error=nil;NSMutableDictionary* root=[NSJSONSerialization JSONObjectWithData:bytes options:NSJSONReadingMutableContainers error:&error];
 if(![root isKindOfClass:NSMutableDictionary.class])return;
 NSMutableDictionary* packs=root[@"TexturePacks"];if(![packs isKindOfClass:NSMutableDictionary.class]){packs=[NSMutableDictionary dictionary];root[@"TexturePacks"]=packs;}
 NSMutableDictionary* azahar=packs[@"Azahar"];if(![azahar isKindOfClass:NSMutableDictionary.class]){azahar=[NSMutableDictionary dictionary];packs[@"Azahar"]=azahar;}
 if([azahar[@"LoadDirectory"] isEqual:url.path])return;
 azahar[@"LoadDirectory"]=url.path;azahar[@"LoadCustomTextures"]=@YES;
 NSData* updated=[NSJSONSerialization dataWithJSONObject:root options:0 error:&error];
 if(!updated||![updated writeToFile:path options:NSDataWritingAtomic error:&error])Status(@"Could not restore texture-folder settings. Choose the folder again.");
}
}
@interface RetunedTexturePicker:NSObject<UIDocumentPickerDelegate>
@end
@implementation RetunedTexturePicker
-(void)documentPickerWasCancelled:(UIDocumentPickerViewController*)controller {Status(@"Folder selection cancelled; existing textures are unchanged.");}
-(void)documentPicker:(UIDocumentPickerViewController*)controller didPickDocumentsAtURLs:(NSArray<NSURL*>*)urls {
 NSURL* url=urls.firstObject;if(!url)return;
 if(![url startAccessingSecurityScopedResource]){Status(@"Could not access that folder. Please select it again in Files.");return;}
 BOOL directory=NO;
 if(![NSFileManager.defaultManager fileExistsAtPath:url.path isDirectory:&directory]||!directory){[url stopAccessingSecurityScopedResource];Status(@"That folder is not available locally. Make it available in Files, then try again.");return;}
 NSError* error=nil;NSData* bookmark=[url bookmarkDataWithOptions:0 includingResourceValuesForKeys:nil relativeToURL:nil error:&error];
 if(!bookmark){[url stopAccessingSecurityScopedResource];Status(@"Could not remember folder access; existing textures are unchanged.");return;}
 [OpenFolders addObject:url];[NSUserDefaults.standardUserDefaults setObject:bookmark forKey:@"RetunedTextureFolderBookmark"];
 Select(url);
}
@end
static RetunedTexturePicker* Picker;
extern "C" void RetunedInitializeTextureFolder(const char* dataDirectory){
 OpenFolders=[NSMutableArray array];Picker=[RetunedTexturePicker new];
 NSData* bookmark=[NSUserDefaults.standardUserDefaults dataForKey:@"RetunedTextureFolderBookmark"];
 if(bookmark){
  BOOL stale=NO;NSError* error=nil;NSURL* url=[NSURL URLByResolvingBookmarkData:bookmark options:0 relativeToURL:nil bookmarkDataIsStale:&stale error:&error];
  if(url&&[url startAccessingSecurityScopedResource]){
   [OpenFolders addObject:url];UpdateConfig([NSString stringWithUTF8String:dataDirectory],url);
   if(stale){NSData* refreshed=[url bookmarkDataWithOptions:0 includingResourceValuesForKeys:nil relativeToURL:nil error:&error];if(refreshed)[NSUserDefaults.standardUserDefaults setObject:refreshed forKey:@"RetunedTextureFolderBookmark"];}
  }else Status(@"Folder access expired. Choose your texture folder again.");
 }
 using namespace RetunedFrontend;
 TextureFolders.TakeSelection=[]{std::lock_guard lock(FolderMutex);auto result=FolderSelection;FolderSelection.clear();return result;};
 TextureFolders.Status=[]{std::lock_guard lock(FolderMutex);return FolderStatus;};
 TextureFolders.Choose=[]{dispatch_async(dispatch_get_main_queue(),^{
  UIWindow* window=nil;
  for(UIScene* scene in UIApplication.sharedApplication.connectedScenes)if([scene isKindOfClass:UIWindowScene.class])for(UIWindow* candidate in ((UIWindowScene*)scene).windows)if(candidate.isKeyWindow)window=candidate;
  UIViewController* controller=window.rootViewController;while(controller.presentedViewController)controller=controller.presentedViewController;
  if(!controller){Status(@"Cannot open Files right now. Try again.");return;}
  UIDocumentPickerViewController* picker=[[UIDocumentPickerViewController alloc]initForOpeningContentTypes:@[UTTypeFolder] asCopy:NO];
  picker.delegate=Picker;picker.allowsMultipleSelection=NO;
  [controller presentViewController:picker animated:YES completion:nil];
 });};
}
