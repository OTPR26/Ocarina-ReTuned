"""Add a single-window scene lifecycle to the pinned SDL UIKit backend."""
from pathlib import Path
import sys

def change(path, before, after):
    text=path.read_text()
    if after in text:return
    if text.count(before)!=1:raise RuntimeError('SDL UIKit context changed: '+path.name)
    path.write_text(text.replace(before,after))

def apply(root):
    root=Path(root)/'src/video/uikit'
    if '@interface RetunedSceneDelegate' not in (root/'SDL_uikitappdelegate.m').read_text():
        change(root/'SDL_uikitappdelegate.m', '@implementation SDLUIKitDelegate {', '''/* Ocarina ReTuned: bridge SDL's main loop to the required UIKit scene lifecycle. */
@interface RetunedSceneDelegate : NSObject <UIWindowSceneDelegate>
@property (nonatomic, strong) UIWindow *window;
@end
@implementation RetunedSceneDelegate
- (void)scene:(UIScene *)scene willConnectToSession:(UISceneSession *)session options:(UISceneConnectionOptions *)options
{
    static BOOL launched = NO;
    if (!launched && [scene isKindOfClass:UIWindowScene.class]) {
        launched = YES;
        [[SDLUIKitDelegate sharedAppDelegate] performSelector:@selector(postFinishLaunch) withObject:nil afterDelay:0.0];
    }
}
@end

@implementation SDLUIKitDelegate {''')
    change(root/'SDL_uikitappdelegate.m','@implementation RetunedSceneDelegate', '''@implementation RetunedSceneDelegate
- (void)sceneWillResignActive:(UIScene *)scene { SDL_OnApplicationWillResignActive(); }
- (void)sceneDidEnterBackground:(UIScene *)scene { SDL_OnApplicationDidEnterBackground(); }
- (void)sceneWillEnterForeground:(UIScene *)scene { SDL_OnApplicationWillEnterForeground(); }
- (void)sceneDidBecomeActive:(UIScene *)scene { SDL_OnApplicationDidBecomeActive(); }''')
    change(root/'SDL_uikitappdelegate.m','    [self performSelector:@selector(postFinishLaunch) withObject:nil afterDelay:0.0];','    /* The scene delegate starts the SDL main loop after its window scene connects. */')
    change(root/'SDL_uikitwindow.m','        uiwindow = [[SDL_uikitwindow alloc] initWithFrame:data.uiscreen.bounds];','''        UIWindowScene *windowScene = nil;
        for (UIScene *scene in UIApplication.sharedApplication.connectedScenes) {
            if ([scene isKindOfClass:UIWindowScene.class] && ((UIWindowScene *)scene).screen == data.uiscreen) {
                windowScene = (UIWindowScene *)scene;
                break;
            }
        }
        if (!windowScene) return SDL_SetError("No connected window scene for this display");
        uiwindow = [[SDL_uikitwindow alloc] initWithWindowScene:windowScene];
        uiwindow.frame = data.uiscreen.bounds;''')

if __name__=='__main__':apply(sys.argv[1])
