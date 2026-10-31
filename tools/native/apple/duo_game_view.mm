// SPDX-License-Identifier: GPL-2.0-or-later
// Optional dual-screen layout; the observer gates it on device capabilities.
#import <UIKit/UIKit.h>
#import <QuartzCore/QuartzCore.h>
#import "duo_layout_observer.h"
#import "duo_equipment_strip.h"
#include "touch_controls.h"
#include <SDL.h>
#include <SDL_syswm.h>
#include "fast/oot3d/retuned_screen_probe.h"
#include "fast/oot3d/retuned_game_save.h"
using namespace RetunedFrontend;
static ScreenRect DuoRect(CGRect r) {return {float(r.origin.x),float(r.origin.y),float(r.size.width),float(r.size.height)};}
@interface RetunedDuoSaveButton : UIButton
- (void)refresh;
@end
@implementation RetunedDuoSaveButton
- (instancetype)initWithFrame:(CGRect)frame {
    if(!(self=[super initWithFrame:frame]))return nil;
    self.accessibilityLabel=@"Save game";
    [self setTitle:@"Save" forState:UIControlStateNormal];
    NSString* data=[NSSearchPathForDirectoriesInDomains(NSApplicationSupportDirectory,NSUserDomainMask,YES).firstObject stringByAppendingPathComponent:@"OcarinaReTuned"];
    UIImage* skin=[UIImage imageWithContentsOfFile:[data stringByAppendingPathComponent:@"lower-equipment/save.png"]];
    if(!skin)skin=[UIImage imageWithContentsOfFile:[NSBundle.mainBundle.bundlePath stringByAppendingPathComponent:@"PrivateGame/lower-equipment/save.png"]];
    if(skin){[self setTitle:nil forState:UIControlStateNormal];[self setImage:skin forState:UIControlStateNormal];self.imageView.contentMode=UIViewContentModeScaleAspectFit;}
    else self.backgroundColor=[UIColor colorWithWhite:.22 alpha:1];
    [self addTarget:self action:@selector(saveGame) forControlEvents:UIControlEventTouchUpInside];
    return self;
}
- (void)saveGame {if(GameSave.Visible())GameSave.Request();}
- (void)refresh {
    const auto picture=DuoDisplay.Layout(self.superview.bounds.size.width,self.superview.bounds.size.height,ProbeGuestDualActive.load()).Lower;
    self.hidden=!self.currentImage||!GameSave.Visible()||!ProbeGuestDualActive.load()||picture.Width<=0||picture.Height<=0;
    self.frame=CGRectMake(picture.X+picture.Width*8/320,picture.Y+picture.Height*64/240,
        picture.Width*40/320,picture.Height*34/240);
    self.titleLabel.font=[UIFont systemFontOfSize:self.bounds.size.height*.29 weight:UIFontWeightMedium];
}
@end
@interface RetunedDuoGameView : NSObject
@property(nonatomic,strong) RetunedDuoLayoutObserver* observer;
@property(nonatomic,strong) CADisplayLink* refreshLink;
@property(nonatomic,strong) RetunedDuoEquipmentStrip* strip;
@property(nonatomic,strong) RetunedDuoSaveButton* saveButton;
@property(nonatomic,weak) UIView* view;
@end
@implementation RetunedDuoGameView
- (instancetype)initWithView:(UIView*)view {
    self=[super init];
    if(!self)return nil;
    _view=view;
    _strip=[[RetunedDuoEquipmentStrip alloc] initWithFrame:CGRectZero];
    [view addSubview:_strip];
    _saveButton=[[RetunedDuoSaveButton alloc] initWithFrame:CGRectZero];
    [view addSubview:_saveButton];
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
- (void)refresh {
    [self.observer refresh];
    RetunedIOS_SetTouchDualLayout(ProbeGuestDualActive.load());
    [self.strip refresh];
    [self.view bringSubviewToFront:self.strip];
    [self.saveButton refresh];
    [self.view bringSubviewToFront:self.saveButton];
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
