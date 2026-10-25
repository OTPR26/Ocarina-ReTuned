// SPDX-License-Identifier: GPL-2.0-or-later
// Standalone layout/input probe. Contains no game, ROM, module, or save data.
#import <UIKit/UIKit.h>
#import <CoreMotion/CoreMotion.h>
#import "duo_layout_observer.h"
#include "screen_mode_policy.h"
#include <vector>

using namespace RetunedFrontend;
static ScreenRect ScreenRectFromCGRect(CGRect r) {
    return {float(r.origin.x), float(r.origin.y), float(r.size.width), float(r.size.height)};
}
static CGRect CGRectFor(ScreenRect r) { return CGRectMake(r.X, r.Y, r.Width, r.Height); }

@interface RetunedProbeCanvas : UIView
@property(nonatomic, copy) void(^layoutHandler)(void);
@property(nonatomic, copy) void(^touchHandler)(CGPoint);
@end
@implementation RetunedProbeCanvas
- (void)layoutSubviews { [super layoutSubviews]; if (self.layoutHandler) self.layoutHandler(); }
- (void)touchesBegan:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event {
    if (self.touchHandler) self.touchHandler([touches.anyObject locationInView:self]);
}
@end

@interface RetunedProbeController : UIViewController {
    GameScreenLayout _gameLayout;
}
@property(nonatomic, strong) RetunedProbeCanvas* canvas;
@property(nonatomic, strong) UILabel* status;
@property(nonatomic, strong) UILabel* top;
@property(nonatomic, strong) UILabel* lower;
@property(nonatomic, strong) UISegmentedControl* selection;
@property(nonatomic, strong) RetunedDuoLayoutObserver* observer;
@property(nonatomic, strong) RetunedDuoLayoutSnapshot* snapshot;
@property(nonatomic, strong) CMMotionManager* motion;
@property(nonatomic) BOOL motionAvailable;
@property(nonatomic) double gravityX;
@property(nonatomic) double gravityY;
@property(nonatomic) double gravityZ;
@end

@implementation RetunedProbeController
- (void)viewDidLoad {
    [super viewDidLoad];
    self.overrideUserInterfaceStyle = UIUserInterfaceStyleDark;
    self.view.backgroundColor = UIColor.blackColor;
    self.selection = [[UISegmentedControl alloc] initWithItems:@[@"Single", @"Dual"]];
    self.selection.selectedSegmentIndex = 0;
    [self.selection addTarget:self action:@selector(selectionChanged) forControlEvents:UIControlEventValueChanged];
    self.status = [UILabel new];
    self.status.numberOfLines = 0;
    self.status.font = [UIFont monospacedSystemFontOfSize:12 weight:UIFontWeightRegular];
    self.status.textColor = UIColor.whiteColor;
    self.canvas = [RetunedProbeCanvas new];
    self.canvas.backgroundColor = UIColor.blackColor;
    for (UIView* view in @[self.selection, self.status, self.canvas]) {
        view.translatesAutoresizingMaskIntoConstraints = NO;
        [self.view addSubview:view];
    }
    UILayoutGuide* safe = self.view.safeAreaLayoutGuide;
    [NSLayoutConstraint activateConstraints:@[
        [self.selection.topAnchor constraintEqualToAnchor:safe.topAnchor constant:8],
        [self.selection.centerXAnchor constraintEqualToAnchor:safe.centerXAnchor],
        [self.selection.widthAnchor constraintEqualToConstant:240],
        [self.status.topAnchor constraintEqualToAnchor:self.selection.bottomAnchor constant:8],
        [self.status.leadingAnchor constraintEqualToAnchor:safe.leadingAnchor constant:12],
        [self.status.trailingAnchor constraintEqualToAnchor:safe.trailingAnchor constant:-12],
        [self.status.heightAnchor constraintEqualToConstant:100],
        [self.canvas.topAnchor constraintEqualToAnchor:self.status.bottomAnchor constant:8],
        [self.canvas.leadingAnchor constraintEqualToAnchor:safe.leadingAnchor],
        [self.canvas.trailingAnchor constraintEqualToAnchor:safe.trailingAnchor],
        [self.canvas.bottomAnchor constraintEqualToAnchor:safe.bottomAnchor]
    ]];
    self.top = [self makePane:@"Top view — adaptive canvas" color:[UIColor colorWithRed:.1 green:.2 blue:.5 alpha:1]];
    self.lower = [self makePane:@"Lower view — native touch 320 × 240" color:[UIColor colorWithRed:.05 green:.35 blue:.2 alpha:1]];
    __weak RetunedProbeController* weakSelf = self;
    self.canvas.layoutHandler = ^{ [weakSelf.observer refresh]; };
    self.canvas.touchHandler = ^(CGPoint point) {
        RetunedProbeController* controller = weakSelf;
        if (!controller) return;
        std::vector<ScreenRect> occlusions;
        for (NSValue* value in controller.snapshot.occlusions)
            occlusions.push_back(ScreenRectFromCGRect(value.CGRectValue));
        const auto touch = MapUnoccludedLowerTouch(controller->_gameLayout, point.x, point.y, occlusions);
        controller.lower.text = touch ? [NSString stringWithFormat:@"Lower touch: %u, %u", touch->X, touch->Y]
                                      : @"Touch rejected outside lower content";
    };
    self.observer = [[RetunedDuoLayoutObserver alloc] initWithView:self.canvas
        handler:^(RetunedDuoLayoutSnapshot* snapshot) {
            weakSelf.snapshot = snapshot;
            [weakSelf updateLayout];
        }];
    self.motion = [CMMotionManager new];
    if (self.motion.deviceMotionAvailable) {
        self.motion.deviceMotionUpdateInterval = 0.1;
        [self.motion startDeviceMotionUpdatesToQueue:NSOperationQueue.mainQueue
            withHandler:^(CMDeviceMotion* motion, NSError* error) {
                RetunedProbeController* controller = weakSelf;
                if (!controller) return;
                controller.motionAvailable = motion != nil && error == nil;
                controller.gravityX = motion ? motion.gravity.x : 0;
                controller.gravityY = motion ? motion.gravity.y : 0;
                controller.gravityZ = motion ? motion.gravity.z : 0;
                [controller updateLayout];
            }];
    }
}
- (UILabel*)makePane:(NSString*)text color:(UIColor*)color {
    UILabel* pane = [UILabel new];
    pane.text = text;
    pane.textColor = UIColor.whiteColor;
    pane.textAlignment = NSTextAlignmentCenter;
    pane.numberOfLines = 0;
    pane.backgroundColor = color;
    // The canvas owns touches in native view coordinates.
    pane.userInteractionEnabled = NO;
    [self.canvas addSubview:pane];
    return pane;
}
- (void)selectionChanged { [self updateLayout]; }
- (void)updateLayout {
    RetunedDuoLayoutSnapshot* snapshot = self.snapshot;
    if (!snapshot) return;
    CGRect division = CGRectZero;
    BOOL dualAvailable = NO;
    for (NSValue* value in snapshot.divisions) {
        const auto candidate = LayoutDividedGameScreens(ScreenRectFromCGRect(snapshot.safeBounds),
            ScreenRectFromCGRect(value.CGRectValue), GamePresentation::Dual);
        if (candidate.Top.Width > 0 && candidate.Lower.Width > 0) {
            division = value.CGRectValue;
            dualAvailable = YES;
            break;
        }
    }
    const bool dual = self.selection.selectedSegmentIndex == 1 && snapshot.phoneWithHinge &&
                      snapshot.hingeStatus != 1 && dualAvailable;
    _gameLayout = LayoutDividedGameScreens(ScreenRectFromCGRect(snapshot.safeBounds), ScreenRectFromCGRect(division),
                        dual ? GamePresentation::Dual : GamePresentation::Single);
    self.top.frame = CGRectFor(_gameLayout.Top);
    self.lower.frame = CGRectFor(_gameLayout.Lower);
    self.lower.hidden = !dual;
    self.status.text = [NSString stringWithFormat:
        @"Ocarina Display Probe • no game data\nHinge: %@  state: %ld  angle: %.2f radians\nCanvas: %.0f × %.0f  divisions: %lu  occlusions: %lu\nMode: %@ • Hybrid posture classification remains disabled",
        snapshot.phoneWithHinge ? @"available" : @"unavailable", (long)snapshot.hingeStatus,
        (double)snapshot.hingeAngleRadians, snapshot.safeBounds.size.width, snapshot.safeBounds.size.height,
        (unsigned long)snapshot.divisions.count, (unsigned long)snapshot.occlusions.count,
        dual ? @"Dual" : @"Single"];
    NSDictionary* receipt = @{
        @"phone_with_hinge": @(snapshot.phoneWithHinge), @"hinge_status": @(snapshot.hingeStatus),
        @"hinge_angle_radians": @(snapshot.hingeAngleRadians),
        @"safe_bounds": NSStringFromCGRect(snapshot.safeBounds),
        @"divisions": [snapshot.divisions valueForKey:@"description"],
        @"occlusions": [snapshot.occlusions valueForKey:@"description"],
        @"orientation": @(snapshot.orientation), @"effective_mode": dual ? @"dual" : @"single",
        @"device_motion_available": @(self.motionAvailable),
        @"gravity": @[@(self.gravityX), @(self.gravityY), @(self.gravityZ)]
    };
    NSString* path = [NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).firstObject
        stringByAppendingPathComponent:@"layout-receipt.json"];
    [[NSJSONSerialization dataWithJSONObject:receipt options:NSJSONWritingPrettyPrinted error:nil]
        writeToFile:path atomically:YES];
}
- (void)viewDidLayoutSubviews { [super viewDidLayoutSubviews]; [self.observer refresh]; }
- (void)viewSafeAreaInsetsDidChange { [super viewSafeAreaInsetsDidChange]; [self.observer refresh]; }
- (void)dealloc { [self.motion stopDeviceMotionUpdates]; [self.observer invalidate]; }
@end

@interface RetunedProbeScene : UIResponder <UIWindowSceneDelegate>
@property(nonatomic, strong) UIWindow* window;
@end
@implementation RetunedProbeScene
- (void)sceneDidBecomeActive:(UIScene*)scene {
    RetunedProbeController* controller = (RetunedProbeController*)self.window.rootViewController;
    [controller.observer refresh];
}
- (void)scene:(UIScene*)scene willConnectToSession:(UISceneSession*)session options:(UISceneConnectionOptions*)options {
    self.window = [[UIWindow alloc] initWithWindowScene:(UIWindowScene*)scene];
    self.window.rootViewController = [RetunedProbeController new];
    [self.window makeKeyAndVisible];
}
@end
@interface RetunedProbeApp : UIResponder <UIApplicationDelegate>
@end
@implementation RetunedProbeApp
@end
int main(int argc, char** argv) {
    @autoreleasepool { return UIApplicationMain(argc, argv, nil, NSStringFromClass(RetunedProbeApp.class)); }
}
