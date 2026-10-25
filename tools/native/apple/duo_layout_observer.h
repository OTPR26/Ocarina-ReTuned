// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#import <UIKit/UIKit.h>

// Raw platform evidence, kept separate from the user's saved screen mode and
// from the guest's acknowledged presentation. No angle-only Hybrid decision.
@interface RetunedDuoLayoutSnapshot : NSObject
@property(nonatomic) BOOL phoneWithHinge;
@property(nonatomic) NSInteger hingeStatus; // 0 unknown, 1 closed, 2 partial, 3 open
@property(nonatomic) CGFloat hingeAngleRadians;
@property(nonatomic) CGRect bounds;
@property(nonatomic) CGRect safeBounds;
@property(nonatomic, copy) NSArray<NSValue*>* divisions;
@property(nonatomic, copy) NSArray<NSValue*>* occlusions;
@property(nonatomic) UIInterfaceOrientation orientation;
@end

@interface RetunedDuoLayoutObserver : NSObject
- (instancetype)initWithView:(UIView*)view
                     handler:(void(^)(RetunedDuoLayoutSnapshot*))handler;
// Call after layout/safe-area changes as well as application reactivation.
- (void)refresh;
- (void)invalidate;
@end
