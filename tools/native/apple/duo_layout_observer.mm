// SPDX-License-Identifier: GPL-2.0-or-later
#import "duo_layout_observer.h"
#if __has_include(<UIKit/UIHingeInteraction.h>)
#import <UIKit/UIHingeInteraction.h>
#import <UIKit/UIViewReservedRegion.h>
#define RETUNED_HAS_DUO_SDK 1
#else
#define RETUNED_HAS_DUO_SDK 0
#endif

@implementation RetunedDuoLayoutSnapshot
@end

@interface RetunedDuoLayoutObserver ()
@property(nonatomic, weak) UIView* view;
@property(nonatomic, copy) void(^handler)(RetunedDuoLayoutSnapshot*);
@property(nonatomic, strong) id interaction;
@property(nonatomic) BOOL hingeAvailable;
@property(nonatomic) NSInteger hingeStatus;
@property(nonatomic) CGFloat hingeAngle;
@end

@implementation RetunedDuoLayoutObserver
- (instancetype)initWithView:(UIView*)view handler:(void(^)(RetunedDuoLayoutSnapshot*))handler {
    NSAssert(NSThread.isMainThread, @"Observe the game view on the main thread");
    self = [super init];
    if (!self) return nil;
    _view = view;
    _handler = [handler copy];
#if RETUNED_HAS_DUO_SDK
    if (@available(iOS 27.1, *)) {
        __weak RetunedDuoLayoutObserver* weakSelf = self;
        UIHingeInteraction* interaction = [[UIHingeInteraction alloc]
            initWithUpdateHandler:^(UIHingeInteraction*, UIHingeInteractionUpdate* update) {
                RetunedDuoLayoutObserver* observer = weakSelf;
                if (!observer) return;
                observer.hingeAvailable = update.hinge != nil;
                observer.hingeStatus = update.hinge ? update.hinge.status : 0;
                observer.hingeAngle = update.hinge ? update.hinge.angle : 0;
                [observer refresh];
            }];
        _interaction = interaction;
        [view addInteraction:interaction];
    }
#endif
    [self refresh];
    return self;
}
- (void)refresh {
    NSAssert(NSThread.isMainThread, @"Read game-view layout on the main thread");
    UIView* view = self.view;
    if (!view || !self.handler) return;
    RetunedDuoLayoutSnapshot* snapshot = [RetunedDuoLayoutSnapshot new];
    snapshot.phoneWithHinge = self.hingeAvailable &&
        view.traitCollection.userInterfaceIdiom == UIUserInterfaceIdiomPhone;
    snapshot.hingeStatus = self.hingeStatus;
    snapshot.hingeAngleRadians = self.hingeAngle;
    snapshot.bounds = view.bounds;
    snapshot.safeBounds = UIEdgeInsetsInsetRect(view.bounds, view.safeAreaInsets);
    snapshot.orientation = view.window.windowScene.interfaceOrientation;
    NSMutableArray<NSValue*>* divisions = [NSMutableArray array];
    NSMutableArray<NSValue*>* occlusions = [NSMutableArray array];
#if RETUNED_HAS_DUO_SDK
    if (@available(iOS 27.1, *)) {
        // Include the inactive fold divider: explicit Dual must also work
        // when the device is flat. Occlusions only exclude active regions.
        for (UIViewReservedRegion* region in [view reservedRegionsOfKind:
                UIViewReservedRegionKind.divisionRegionKind
                options:UIViewReservedRegionQueryOptionsIncludeInactive]) {
            [divisions addObject:[NSValue valueWithCGRect:region.frame]];
        }
        for (UIViewReservedRegion* region in [view reservedRegionsOfKind:
                UIViewReservedRegionKind.occlusionRegionKind]) {
            if (region.active) [occlusions addObject:[NSValue valueWithCGRect:region.frame]];
        }
    }
#endif
    snapshot.divisions = divisions;
    snapshot.occlusions = occlusions;
    self.handler(snapshot);
}
- (void)invalidate {
    NSAssert(NSThread.isMainThread, @"Detach the game view on the main thread");
    if (self.interaction && self.view) [self.view removeInteraction:self.interaction];
    self.interaction = nil;
    self.handler = nil;
    self.view = nil;
    self.hingeAvailable = NO;
}
@end
