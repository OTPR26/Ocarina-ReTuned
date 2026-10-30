// SPDX-License-Identifier: GPL-2.0-or-later
#import <UIKit/UIKit.h>
#import <TargetConditionals.h>
#include "startup_status.h"

@interface RetunedSetupController : UIViewController
@property(nonatomic) RetunedAppleStartupIssue issue;
#if TARGET_OS_TV
@property(nonatomic,strong) UITextView* steps;
#else
@property(nonatomic,strong) UILabel* steps;
#endif
@property(nonatomic,strong) UIButton* stepsButton;
@end

@implementation RetunedSetupController
- (void)viewDidLoad {
    [super viewDidLoad];
    self.view.backgroundColor=[UIColor colorWithRed:.035 green:.055 blue:.065 alpha:1];
    UIScrollView* scroll=[UIScrollView new];scroll.translatesAutoresizingMaskIntoConstraints=NO;
    [self.view addSubview:scroll];
    UIStackView* stack=[UIStackView new];stack.axis=UILayoutConstraintAxisVertical;stack.spacing=22;
    stack.translatesAutoresizingMaskIntoConstraints=NO;[scroll addSubview:stack];
#if TARGET_OS_TV
    CGFloat margin=80, maxWidth=1000, titleSize=48, bodySize=28, buttonHeight=72;
#else
    CGFloat margin=24, maxWidth=760, titleSize=30, bodySize=18, buttonHeight=52;
#endif
    UILayoutGuide* safe=self.view.safeAreaLayoutGuide;
    [NSLayoutConstraint activateConstraints:@[
        [scroll.topAnchor constraintEqualToAnchor:safe.topAnchor constant:margin],
        [scroll.bottomAnchor constraintEqualToAnchor:safe.bottomAnchor constant:-margin],
        [scroll.leadingAnchor constraintEqualToAnchor:safe.leadingAnchor constant:margin],
        [scroll.trailingAnchor constraintEqualToAnchor:safe.trailingAnchor constant:-margin],
        [stack.topAnchor constraintEqualToAnchor:scroll.contentLayoutGuide.topAnchor],
        [stack.bottomAnchor constraintEqualToAnchor:scroll.contentLayoutGuide.bottomAnchor constant:-24],
        [stack.centerXAnchor constraintEqualToAnchor:scroll.frameLayoutGuide.centerXAnchor],
        [stack.leadingAnchor constraintGreaterThanOrEqualToAnchor:scroll.contentLayoutGuide.leadingAnchor],
        [stack.trailingAnchor constraintLessThanOrEqualToAnchor:scroll.contentLayoutGuide.trailingAnchor],
        [stack.widthAnchor constraintLessThanOrEqualToConstant:maxWidth],
    ]];
    // A wide display caps the text column instead of stretching each line.
    NSLayoutConstraint* columnWidth=[stack.widthAnchor constraintEqualToAnchor:scroll.frameLayoutGuide.widthAnchor];
    columnWidth.priority=UILayoutPriorityDefaultHigh;columnWidth.active=YES;
    UILabel* brand=[UILabel new];brand.text=@"Ocarina ReTuned";brand.textColor=[UIColor colorWithRed:.5 green:.9 blue:.7 alpha:1];
    brand.font=[UIFont systemFontOfSize:bodySize weight:UIFontWeightSemibold];[stack addArrangedSubview:brand];
    UILabel* title=[UILabel new];title.numberOfLines=0;title.textColor=UIColor.whiteColor;
    title.font=[UIFont systemFontOfSize:titleSize weight:UIFontWeightBold];
    title.text=self.issue==RetunedAppleStartupMissingGame?@"Game setup required":@"Game could not start";
    title.accessibilityIdentifier=@"startup-title";[stack addArrangedSubview:title];
    UILabel* message=[UILabel new];message.numberOfLines=0;message.textColor=UIColor.whiteColor;
    message.font=[UIFont systemFontOfSize:bodySize];message.accessibilityIdentifier=@"startup-message";
    switch(self.issue) {
        case RetunedAppleStartupMissingGame:
            message.text=@"This download does not contain a prepared game. Signing and installing the IPA alone will not start it. Prepare your own supported ROM on a Mac, then sign and install the resulting private IPA.";break;
        case RetunedAppleStartupInvalidSetup:
            message.text=@"The prepared game files are incomplete or invalid. Prepare a new IPA from your supported ROM on a Mac. Keep your current saves when updating the app.";break;
        case RetunedAppleStartupMissingModule:
            message.text=@"The prepared game module is missing. Use the IPA produced by the Mac preparation tool, and make sure your signing tool retains and signs its embedded frameworks.";break;
        case RetunedAppleStartupStorageError:
            message.text=@"The app could not read or write its local setup files. Check free storage, restart the app, and try again. Do not delete the app to troubleshoot, because that can remove local saves.";break;
        default:
            message.text=@"The prepared game encountered a startup error. Check that the game was prepared for this device platform and that all embedded frameworks were signed. Include your device, OS version, signing tool, and whether Mac preparation completed when reporting this problem.";break;
    }
    [stack addArrangedSubview:message];
    self.stepsButton=[UIButton buttonWithType:UIButtonTypeSystem];
    UIButtonConfiguration* style=[UIButtonConfiguration filledButtonConfiguration];style.title=@"Setup instructions";
    style.baseBackgroundColor=[UIColor colorWithRed:.12 green:.38 blue:.28 alpha:1];style.baseForegroundColor=UIColor.whiteColor;
    self.stepsButton.configuration=style;self.stepsButton.accessibilityIdentifier=@"setup-instructions";
    [self.stepsButton.heightAnchor constraintGreaterThanOrEqualToConstant:buttonHeight].active=YES;
    [self.stepsButton addTarget:self action:@selector(toggleInstructions) forControlEvents:UIControlEventPrimaryActionTriggered];
    [stack addArrangedSubview:self.stepsButton];
#if TARGET_OS_TV
    self.steps=[UITextView new];self.steps.selectable=YES;
    self.steps.backgroundColor=UIColor.clearColor;self.steps.textContainerInset=UIEdgeInsetsZero;
    [self.steps.heightAnchor constraintEqualToConstant:300].active=YES;
#else
    self.steps=[UILabel new];self.steps.numberOfLines=0;
#endif
    self.steps.textColor=UIColor.whiteColor;self.steps.font=[UIFont systemFontOfSize:bodySize];
    self.steps.text=@"1. On a Mac, download the Mac Preview and the unsigned IPA for your device.\n\n2. Follow the Apple preparation guide using your supported decrypted ROM and your own signing profile. The tool is prepare_apple_app.py in the Mac app’s preparation toolkit.\n\n3. Sign and install the prepared IPA, including its embedded frameworks. Keep the same app identity to preserve existing saves.\n\nThe prepared IPA contains your game data. Keep it private.\n\nGuide: github.com/OTPR26/Ocarina-ReTuned → documentation → Apple setup";
    self.steps.accessibilityIdentifier=@"setup-steps";self.steps.hidden=YES;[stack addArrangedSubview:self.steps];
    UILabel* code=[UILabel new];code.numberOfLines=0;code.font=[UIFont monospacedSystemFontOfSize:bodySize-3 weight:UIFontWeightRegular];
    code.textColor=UIColor.lightGrayColor;code.text=[NSString stringWithFormat:@"Startup code: APPLE-%ld",(long)self.issue];[stack addArrangedSubview:code];
}
- (void)toggleInstructions {
    self.steps.hidden=!self.steps.hidden;
    UIButtonConfiguration* config=self.stepsButton.configuration;config.title=self.steps.hidden?@"Setup instructions":@"Hide instructions";self.stepsButton.configuration=config;
#if TARGET_OS_TV
    [self setNeedsFocusUpdate];[self updateFocusIfNeeded];
#endif
}
- (NSArray<id<UIFocusEnvironment>>*)preferredFocusEnvironments {
#if TARGET_OS_TV
    if(self.steps && !self.steps.hidden)return @[self.steps];
#endif
    return self.stepsButton?@[self.stepsButton]:@[self.view];
}
@end

static UIWindow* RetunedSetupWindow;
int RetunedPresentAppleStartupIssue(RetunedAppleStartupIssue issue) {
    void (^show)(void)=^{
        UIWindowScene* selected=nil;
        for(UIScene* scene in UIApplication.sharedApplication.connectedScenes)
            if([scene isKindOfClass:UIWindowScene.class] && scene.activationState!=UISceneActivationStateUnattached){selected=(UIWindowScene*)scene;break;}
        if(!selected)return;
        RetunedSetupController* controller=[RetunedSetupController new];controller.issue=issue;
        RetunedSetupWindow=[[UIWindow alloc] initWithWindowScene:selected];
        RetunedSetupWindow.rootViewController=controller;[RetunedSetupWindow makeKeyAndVisible];
        [controller setNeedsFocusUpdate];
    };
    if(NSThread.isMainThread)show();else dispatch_sync(dispatch_get_main_queue(),show);
    return 1;
}
