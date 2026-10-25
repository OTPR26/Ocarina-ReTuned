// SPDX-License-Identifier: GPL-2.0-or-later
// Opt-in playable diagnostic. Not part of normal release staging.
#import <UIKit/UIKit.h>
#import <QuartzCore/QuartzCore.h>
#import "duo_layout_observer.h"
#include <SDL.h>
#include <SDL_syswm.h>
#include "fast/oot3d/retuned_screen_probe.h"
using namespace RetunedFrontend;
static ScreenRect DuoRect(CGRect r) {return {float(r.origin.x),float(r.origin.y),float(r.size.width),float(r.size.height)};}
@interface RetunedDuoGameView : NSObject
@property(nonatomic,strong) RetunedDuoLayoutObserver* observer;
@property(nonatomic,strong) CADisplayLink* refreshLink;
@property(nonatomic,strong) UISegmentedControl* selector;
@property(nonatomic,weak) UIView* view;
@end
@implementation RetunedDuoGameView
- (instancetype)initWithView:(UIView*)view {
    self=[super init];
    if(!self)return nil;
    _view=view;
    _selector=[[UISegmentedControl alloc] initWithItems:@[@"Single",@"Dual"]];
    _selector.selectedSegmentIndex=0;
    _selector.overrideUserInterfaceStyle=UIUserInterfaceStyleDark;
    [_selector addTarget:self action:@selector(selectMode) forControlEvents:UIControlEventValueChanged];
    [view addSubview:_selector];
    _observer=[[RetunedDuoLayoutObserver alloc] initWithView:view handler:^(RetunedDuoLayoutSnapshot* snapshot) {
        DuoDisplayGeometry geometry;
        geometry.Available=snapshot.phoneWithHinge;
        geometry.Closed=snapshot.hingeStatus==0 || snapshot.hingeStatus==1;
        geometry.Bounds=DuoRect(snapshot.bounds);geometry.Safe=DuoRect(snapshot.safeBounds);
        for(NSValue* value in snapshot.divisions) {
            auto candidate=LayoutDividedGameScreens(geometry.Safe,DuoRect(value.CGRectValue),GamePresentation::Dual);
            if(candidate.Lower.Width>0){geometry.Division=DuoRect(value.CGRectValue);break;}
        }
        for(NSValue* value in snapshot.occlusions)geometry.Occlusions.push_back(DuoRect(value.CGRectValue));
        DuoDisplay.Publish(std::move(geometry));
    }];
    _refreshLink=[CADisplayLink displayLinkWithTarget:self selector:@selector(refresh)];
    _refreshLink.preferredFramesPerSecond=30;
    [_refreshLink addToRunLoop:NSRunLoop.mainRunLoop forMode:NSRunLoopCommonModes];
    [self refresh];return self;
}
- (void)selectMode {DuoDisplay.Select(self.selector.selectedSegmentIndex==1?ScreenPreference::Dual:ScreenPreference::Single);}
- (void)refresh {
    [self.observer refresh];
    const CGRect safe=UIEdgeInsetsInsetRect(self.view.bounds,self.view.safeAreaInsets);
    self.selector.frame=CGRectMake(CGRectGetMinX(safe)+8,CGRectGetMinY(safe)+8,180,30);
    [self.view bringSubviewToFront:self.selector];
}
@end
static RetunedDuoGameView* sDuoGameView;
extern "C" void RetunedAttachDuoGameView(SDL_Window* window) {
    if(!DuoProbeRequested())return;
    SDL_SysWMinfo info;SDL_VERSION(&info.version);
    if(!SDL_GetWindowWMInfo(window,&info) || info.subsystem!=SDL_SYSWM_UIKIT)return;
    UIWindow* uiwindow=info.info.uikit.window;
    void(^attach)(void)=^{
        if(sDuoGameView)return;
        UIView* view=uiwindow.rootViewController.view;
        sDuoGameView=[[RetunedDuoGameView alloc] initWithView:view];
    };
    if(NSThread.isMainThread)attach();else dispatch_async(dispatch_get_main_queue(),attach);
}
