// Touch presentation adapted from Linkzenic's Ship of Harkinian iOS port.
#import <UIKit/UIKit.h>

#include <SDL.h>
#include <algorithm>
#include <atomic>
#include <cmath>

#include "touch_controls.h"
#include "touch_input_api.h"
#include "touch_dpad.h"

namespace {

constexpr int kButtonA = 0;
constexpr int kButtonB = 1;
constexpr int kButtonX = 2;
constexpr int kButtonY = 3;
constexpr int kButtonBack = 4;
constexpr int kButtonStart = 6;
constexpr int kButtonLeftShoulder = 9;
constexpr int kButtonRightShoulder = 10;
constexpr int kButtonDpadUp = 11;
constexpr int kButtonDpadDown = 12;
constexpr int kButtonDpadLeft = 13;
constexpr int kButtonDpadRight = 14;

constexpr int kAxisLeftX = 0;
constexpr int kAxisLeftY = 1;
constexpr int kAxisRightX = 2;
constexpr int kAxisRightY = 3;
constexpr int kAxisLeftTrigger = 4;
constexpr int kAxisRightTrigger = 5;

void SetVirtualButton(int button, bool pressed) { RetunedTouchSetButton(button,pressed); }
void SetVirtualAxis(int axis, Sint16 value) { RetunedTouchSetAxis(axis,value); }

Sint16 ClampAxis(CGFloat value) {
    return static_cast<Sint16>(
        std::clamp(value, static_cast<CGFloat>(SDL_MIN_SINT16),
                   static_cast<CGFloat>(SDL_MAX_SINT16)));
}

CGFloat sArtworkOpacity=.28;
CGFloat ArtworkAlpha(CGFloat alpha){return MIN(1.0,alpha*sArtworkOpacity/.28);}
UIColor* AndroidControlFill() {
    return [UIColor colorWithWhite:1.0 alpha:ArtworkAlpha(0.125)];
}

UIColor* AndroidControlPressedFill() {
    return [UIColor colorWithWhite:1.0 alpha:ArtworkAlpha(0.063)];
}

UIColor* AndroidControlStroke() {
    return [UIColor colorWithWhite:1.0 alpha:ArtworkAlpha(0.145)];
}

} // namespace

typedef NS_ENUM(NSInteger, RetunedButtonShape) {
    RetunedButtonShapeCircle,
    RetunedButtonShapeRectangle,
    RetunedButtonShapeLeftShoulder,
    RetunedButtonShapeRightShoulder,
    RetunedButtonShapeTransparent,
};

@interface RetunedTouchButton : UIButton

@property(nonatomic) int controllerButton;
@property(nonatomic) int controllerAxis;
@property(nonatomic) Sint16 pressedAxisValue;
@property(nonatomic) Sint16 releasedAxisValue;
@property(nonatomic) BOOL inputPressed;
@property(nonatomic, strong) CAShapeLayer* artwork;
@property(nonatomic) RetunedButtonShape controlShape;
@property(nonatomic) BOOL hudIcon;

- (instancetype)initWithLabel:(NSString*)label
                       button:(int)button
                        shape:(RetunedButtonShape)shape;
- (instancetype)initWithLabel:(NSString*)label
                         axis:(int)axis
                        value:(Sint16)value
                 releaseValue:(Sint16)releaseValue
                        shape:(RetunedButtonShape)shape;
- (void)cancelInput;

@end

@implementation RetunedTouchButton

- (instancetype)initBaseWithLabel:(NSString*)label shape:(RetunedButtonShape)shape {
    self = [super initWithFrame:CGRectZero];
    if (self != nil) {
        self.controllerButton = -1;
        self.controllerAxis = -1;
        self.controlShape = shape;
        self.multipleTouchEnabled = YES;
        self.backgroundColor = AndroidControlFill();
        self.layer.borderColor = AndroidControlStroke().CGColor;
        self.layer.borderWidth = 0;
        self.artwork=[CAShapeLayer layer];
        [self.layer insertSublayer:self.artwork atIndex:0];
        [self setTitle:label forState:UIControlStateNormal];
        [self setTitleColor:AndroidControlStroke() forState:UIControlStateNormal];
        self.titleLabel.font = [UIFont systemFontOfSize:14.0 weight:UIFontWeightSemibold];
        self.accessibilityLabel = label;

        [self addTarget:self
                      action:@selector(inputDown)
            forControlEvents:UIControlEventTouchDown | UIControlEventTouchDragEnter];
        [self addTarget:self
                      action:@selector(inputUp)
            forControlEvents:UIControlEventTouchUpInside | UIControlEventTouchUpOutside |
                             UIControlEventTouchCancel | UIControlEventTouchDragExit];
    }
    return self;
}

- (instancetype)initWithLabel:(NSString*)label
                       button:(int)button
                        shape:(RetunedButtonShape)shape {
    self = [self initBaseWithLabel:label shape:shape];
    if (self != nil) {
        self.controllerButton = button;
    }
    return self;
}

- (instancetype)initWithLabel:(NSString*)label
                         axis:(int)axis
                        value:(Sint16)value
                 releaseValue:(Sint16)releaseValue
                        shape:(RetunedButtonShape)shape {
    self = [self initBaseWithLabel:label shape:shape];
    if (self != nil) {
        self.controllerAxis = axis;
        self.pressedAxisValue = value;
        self.releasedAxisValue = releaseValue;
    }
    return self;
}

- (void)layoutSubviews {
    [super layoutSubviews];
    self.titleLabel.font=[UIFont systemFontOfSize:self.hudIcon?10:14 weight:UIFontWeightSemibold];
    if(self.hudIcon)self.titleLabel.frame=CGRectMake(CGRectGetWidth(self.bounds)*.67,CGRectGetHeight(self.bounds)*.66,CGRectGetWidth(self.bounds)*.28,CGRectGetHeight(self.bounds)*.3);
    self.backgroundColor=UIColor.clearColor;
    self.layer.cornerRadius=0;
    self.artwork.frame=self.bounds;
    self.artwork.hidden=self.controlShape==RetunedButtonShapeTransparent;
    if(self.artwork.hidden)return;
    CGRect r=CGRectInset(self.bounds,1.25,1.25);
    UIBezierPath* path;
    if(self.controlShape==RetunedButtonShapeCircle)path=[UIBezierPath bezierPathWithOvalInRect:r];
    else {
        // Android Ship drawables use a 50dp outer top corner and 10dp
        // corners elsewhere. Normalize adjoining radii to the button height.
        CGFloat tl=10,tr=10,bl=10,br=10;
        if(self.controlShape==RetunedButtonShapeLeftShoulder)tl=50;
        if(self.controlShape==RetunedButtonShapeRightShoulder)tr=50;
        CGFloat k=MIN(1.0,MIN(CGRectGetWidth(r)/MAX(tl+tr,bl+br),CGRectGetHeight(r)/MAX(tl+bl,tr+br)));
        tl*=k;tr*=k;bl*=k;br*=k;
        CGFloat x=CGRectGetMinX(r),y=CGRectGetMinY(r),w=CGRectGetWidth(r),h=CGRectGetHeight(r);
        path=[UIBezierPath bezierPath];
        [path moveToPoint:CGPointMake(x+tl,y)];[path addLineToPoint:CGPointMake(x+w-tr,y)];
        [path addArcWithCenter:CGPointMake(x+w-tr,y+tr) radius:tr startAngle:-M_PI_2 endAngle:0 clockwise:YES];
        [path addLineToPoint:CGPointMake(x+w,y+h-br)];
        [path addArcWithCenter:CGPointMake(x+w-br,y+h-br) radius:br startAngle:0 endAngle:M_PI_2 clockwise:YES];
        [path addLineToPoint:CGPointMake(x+bl,y+h)];
        [path addArcWithCenter:CGPointMake(x+bl,y+h-bl) radius:bl startAngle:M_PI_2 endAngle:M_PI clockwise:YES];
        [path addLineToPoint:CGPointMake(x,y+tl)];
        [path addArcWithCenter:CGPointMake(x+tl,y+tl) radius:tl startAngle:M_PI endAngle:M_PI*1.5 clockwise:YES];
        [path closePath];
    }
    self.artwork.path=path.CGPath;
    self.artwork.fillColor=(self.hudIcon?UIColor.clearColor:(self.inputPressed?AndroidControlPressedFill():AndroidControlFill())).CGColor;
    self.artwork.strokeColor=AndroidControlStroke().CGColor;
    self.artwork.lineWidth=2.5;
}

- (void)inputDown {
    if (self.inputPressed) {
        return;
    }
    self.inputPressed = YES;
    self.artwork.fillColor=(self.hudIcon?UIColor.clearColor:AndroidControlPressedFill()).CGColor;
    if (self.controllerButton >= 0) {
        SetVirtualButton(self.controllerButton, true);
    } else if (self.controllerAxis >= 0) {
        SetVirtualAxis(self.controllerAxis, self.pressedAxisValue);
    }
}

- (void)inputUp {
    if (!self.inputPressed) {
        return;
    }
    self.inputPressed = NO;
    self.artwork.fillColor=(self.hudIcon?UIColor.clearColor:AndroidControlFill()).CGColor;
    if (self.controllerButton >= 0) {
        SetVirtualButton(self.controllerButton, false);
    } else if (self.controllerAxis >= 0) {
        SetVirtualAxis(self.controllerAxis, self.releasedAxisValue);
    }
}

- (void)cancelInput {
    [self inputUp];
}

@end

@interface RetunedTouchStick : UIView

@property(nonatomic, strong) UIView* base;
@property(nonatomic, strong) UIView* knob;
@property(nonatomic) CGPoint stickCenter;
@property(nonatomic) CGFloat stickDiameter;
@property(nonatomic) int controllerAxisX;
@property(nonatomic) int controllerAxisY;
@property(nonatomic) BOOL floating;
- (void)cancelInput;

@end

@implementation RetunedTouchStick

- (instancetype)initWithFrame:(CGRect)frame {
    self = [super initWithFrame:frame];
    if (self != nil) {
        self.multipleTouchEnabled = NO;
        self.backgroundColor = UIColor.clearColor;
        self.accessibilityLabel = @"Floating left joystick";
        self.controllerAxisX = kAxisLeftX;
        self.controllerAxisY = kAxisLeftY;
        _floating = YES;

        self.base = [[UIView alloc] initWithFrame:CGRectZero];
        self.base.userInteractionEnabled = NO;
        self.base.backgroundColor = [UIColor colorWithWhite:0.0 alpha:0.188];
        self.base.layer.borderColor = AndroidControlStroke().CGColor;
        self.base.layer.borderWidth = 2.0;
        self.base.hidden = YES;
        [self addSubview:self.base];

        self.knob = [[UIView alloc] initWithFrame:CGRectZero];
        self.knob.userInteractionEnabled = NO;
        self.knob.backgroundColor = AndroidControlFill();
        self.knob.layer.borderColor = AndroidControlStroke().CGColor;
        self.knob.layer.borderWidth = 2.5;
        [self.base addSubview:self.knob];
    }
    return self;
}

- (void)layoutSubviews {
    [super layoutSubviews];
    CGFloat diameter = self.stickDiameter > 0.0 ? self.stickDiameter : 150.0;
    self.base.bounds = CGRectMake(0.0, 0.0, diameter, diameter);
    self.base.layer.cornerRadius = diameter * 0.5;
    CGFloat knobSize = diameter * 0.32;
    self.knob.bounds = CGRectMake(0.0, 0.0, knobSize, knobSize);
    self.knob.layer.cornerRadius = knobSize * 0.5;
    self.knob.center = CGPointMake(diameter * 0.5, diameter * 0.5);
    if (!self.floating) {
        self.stickCenter = CGPointMake(MAX(diameter * 0.58, CGRectGetWidth(self.bounds) * 0.24),
                                       CGRectGetHeight(self.bounds) - diameter * 0.58);
        self.base.center = self.stickCenter;
        self.base.hidden = NO;
    }
}

- (void)updateForPoint:(CGPoint)point {
    CGPoint center = self.stickCenter;
    CGFloat knobRadius = CGRectGetWidth(self.knob.bounds) * 0.5;
    CGFloat radius = self.stickDiameter * 0.5 - knobRadius;
    CGFloat dx = point.x - center.x;
    CGFloat dy = point.y - center.y;
    CGFloat distance = hypot(dx, dy);
    if (distance > radius && distance > 0.0) {
        dx = dx / distance * radius;
        dy = dy / distance * radius;
    }

    self.knob.center =
        CGPointMake(self.stickDiameter * 0.5 + dx, self.stickDiameter * 0.5 + dy);
    SetVirtualAxis(self.controllerAxisX, ClampAxis((dx / radius) * SDL_MAX_SINT16));
    SetVirtualAxis(self.controllerAxisY, ClampAxis((dy / radius) * SDL_MAX_SINT16));
}

- (void)touchesBegan:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event {
    UITouch* touch = touches.anyObject;
    if (touch != nil) {
        CGPoint point = [touch locationInView:self];
        if (self.floating) {
            self.stickCenter = point;
            self.base.center = self.stickCenter;
        }
        self.base.hidden = NO;
        [self updateForPoint:point];
    }
}

- (void)touchesMoved:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event {
    UITouch* touch = touches.anyObject;
    if (touch != nil) {
        [self updateForPoint:[touch locationInView:self]];
    }
}

- (void)touchesEnded:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event {
    [self cancelInput];
}

- (void)touchesCancelled:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event {
    [self cancelInput];
}

- (void)cancelInput {
    SetVirtualAxis(self.controllerAxisX, 0);
    SetVirtualAxis(self.controllerAxisY, 0);
    self.knob.center =
        CGPointMake(self.stickDiameter * 0.5, self.stickDiameter * 0.5);
    self.base.hidden = self.floating;
}

- (void)setFloating:(BOOL)floating {
    _floating = floating;
    [self cancelInput];
    [self setNeedsLayout];
}

@end

@interface RetunedCrossView : UIView
@property(nonatomic) BOOL hudIcons;
@end

@implementation RetunedCrossView

- (instancetype)initWithFrame:(CGRect)frame {
    self = [super initWithFrame:frame];
    if (self != nil) {
        self.userInteractionEnabled = NO;
        self.backgroundColor = UIColor.clearColor;
    }
    return self;
}

- (void)drawRect:(CGRect)rect {
    CGContextRef context=UIGraphicsGetCurrentContext();
    CGContextSaveGState(context);
    CGContextScaleCTM(context,CGRectGetWidth(rect)/221.78,CGRectGetHeight(rect)/221.78);
    CGContextSetLineWidth(context,2.5);
    for(unsigned i=0;i<(self.hudIcons?1u:5u);++i) {
        CGPathRef path=RetunedDpadPath(i);
        CGContextAddPath(context,path);
        CGContextSetFillColorWithColor(context,(i==0?AndroidControlFill():AndroidControlStroke()).CGColor);
        CGContextSetStrokeColorWithColor(context,AndroidControlStroke().CGColor);
        CGContextDrawPath(context,i==0?(self.hudIcons?kCGPathStroke:kCGPathFillStroke):kCGPathFill);
        CGPathRelease(path);
    }
    CGContextRestoreGState(context);
}

@end

@interface RetunedTouchOverlay : UIView

@property(nonatomic, strong) UIView* controlGroup;
@property(nonatomic, strong) RetunedTouchStick* leftStick;
@property(nonatomic, strong) RetunedTouchStick* rightStick;
@property(nonatomic, strong) RetunedCrossView* cCross;
@property(nonatomic, strong) RetunedTouchButton* buttonA;
@property(nonatomic, strong) RetunedTouchButton* buttonB;
@property(nonatomic, strong) RetunedTouchButton* buttonX;
@property(nonatomic, strong) RetunedTouchButton* buttonY;
@property(nonatomic, strong) RetunedTouchButton* buttonL;
@property(nonatomic, strong) RetunedTouchButton* buttonZL;
@property(nonatomic, strong) RetunedTouchButton* buttonZR;
@property(nonatomic, strong) RetunedTouchButton* buttonR;
@property(nonatomic, strong) RetunedTouchButton* buttonBack;
@property(nonatomic, strong) RetunedTouchButton* buttonStart;
@property(nonatomic, strong) NSArray<RetunedTouchButton*>* cButtons;
@property(nonatomic, strong) NSArray<RetunedTouchButton*>* allInputButtons;
@property(nonatomic, strong) UIButton* visibilityButton;
@property(nonatomic) BOOL controlsHiddenByUser;
@property(nonatomic) BOOL menuVisible;
@property(nonatomic) CGFloat controlScale;
@property(nonatomic) BOOL extraShoulders;
@property(nonatomic) NSInteger faceButtonLayout;

- (void)cancelAllInputs;
- (void)setRetunedFaceButtonLayout:(NSInteger)layout;
- (void)setRetunedMenuVisible:(BOOL)visible;

@end

@implementation RetunedTouchOverlay

- (instancetype)initWithFrame:(CGRect)frame {
    self = [super initWithFrame:frame];
    if (self != nil) {
        self.backgroundColor = UIColor.clearColor;
        self.multipleTouchEnabled = YES;
        self.faceButtonLayout = 0;
        self.controlScale = 1;

        self.controlGroup = [[UIView alloc] initWithFrame:self.bounds];
        self.controlGroup.backgroundColor = UIColor.clearColor;
        self.controlGroup.multipleTouchEnabled = YES;
        self.controlGroup.autoresizingMask =
            UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
        [self addSubview:self.controlGroup];

        self.leftStick = [[RetunedTouchStick alloc] initWithFrame:CGRectZero];
        self.rightStick = [[RetunedTouchStick alloc] initWithFrame:CGRectZero];
        self.rightStick.controllerAxisX = kAxisRightX;
        self.rightStick.controllerAxisY = kAxisRightY;
        self.rightStick.accessibilityLabel = @"Floating right joystick";
        self.cCross = [[RetunedCrossView alloc] initWithFrame:CGRectZero];

        self.buttonA = [[RetunedTouchButton alloc] initWithLabel:@"A"
                                                            button:kButtonA
                                                             shape:RetunedButtonShapeCircle];
        self.buttonB = [[RetunedTouchButton alloc] initWithLabel:@"B"
                                                            button:kButtonB
                                                             shape:RetunedButtonShapeCircle];
        self.buttonX = [[RetunedTouchButton alloc] initWithLabel:@"X"
                                                            button:kButtonX
                                                             shape:RetunedButtonShapeCircle];
        self.buttonY = [[RetunedTouchButton alloc] initWithLabel:@"Y"
                                                            button:kButtonY
                                                             shape:RetunedButtonShapeCircle];
        self.buttonL =
            [[RetunedTouchButton alloc] initWithLabel:@"L"
                                                 button:kButtonLeftShoulder
                                                  shape:RetunedButtonShapeLeftShoulder];
        self.buttonZL =
            [[RetunedTouchButton alloc] initWithLabel:@"ZL"
                                                   axis:kAxisLeftTrigger
                                                  value:SDL_MAX_SINT16
                                           releaseValue:SDL_MIN_SINT16
                                                  shape:RetunedButtonShapeLeftShoulder];
        self.buttonZR =
            [[RetunedTouchButton alloc] initWithLabel:@"ZR"
                                                   axis:kAxisRightTrigger
                                                  value:SDL_MAX_SINT16
                                           releaseValue:SDL_MIN_SINT16
                                                  shape:RetunedButtonShapeRightShoulder];
        self.buttonR =
            [[RetunedTouchButton alloc] initWithLabel:@"R"
                                                 button:kButtonRightShoulder
                                                  shape:RetunedButtonShapeRightShoulder];
        self.buttonBack =
            [[RetunedTouchButton alloc] initWithLabel:@"Settings"
                                                 button:kButtonBack
                                                  shape:RetunedButtonShapeRectangle];
        self.buttonStart =
            [[RetunedTouchButton alloc] initWithLabel:@"Start"
                                                 button:kButtonStart
                                                  shape:RetunedButtonShapeRectangle];

        RetunedTouchButton* cUp =
            [[RetunedTouchButton alloc] initWithLabel:@""
                                                 button:kButtonDpadUp
                                                  shape:RetunedButtonShapeTransparent];
        RetunedTouchButton* cDown =
            [[RetunedTouchButton alloc] initWithLabel:@""
                                                 button:kButtonDpadDown
                                                  shape:RetunedButtonShapeTransparent];
        RetunedTouchButton* cLeft =
            [[RetunedTouchButton alloc] initWithLabel:@""
                                                 button:kButtonDpadLeft
                                                  shape:RetunedButtonShapeTransparent];
        RetunedTouchButton* cRight =
            [[RetunedTouchButton alloc] initWithLabel:@""
                                                 button:kButtonDpadRight
                                                  shape:RetunedButtonShapeTransparent];
        for (RetunedTouchButton* button in @[ cUp, cDown, cLeft, cRight ]) {
            button.backgroundColor = UIColor.clearColor;
            button.layer.borderWidth = 0.0;
        }
        cUp.accessibilityLabel = @"D-pad up";
        cDown.accessibilityLabel = @"D-pad down";
        cLeft.accessibilityLabel = @"D-pad left";
        cRight.accessibilityLabel = @"D-pad right";
        self.cButtons = @[ cUp, cDown, cLeft, cRight ];

        [self.controlGroup addSubview:self.leftStick];
        [self.controlGroup addSubview:self.rightStick];
        [self.controlGroup addSubview:self.cCross];

        self.allInputButtons = @[
            self.buttonA, self.buttonB, self.buttonX, self.buttonY, self.buttonL,
            self.buttonZL, self.buttonZR, self.buttonR, self.buttonBack, self.buttonStart,
            cUp, cDown, cLeft, cRight,
        ];
        for (RetunedTouchButton* button in self.allInputButtons) {
            [self.controlGroup addSubview:button];
        }


        self.visibilityButton = [UIButton buttonWithType:UIButtonTypeCustom];
        self.visibilityButton.backgroundColor = UIColor.clearColor;
        [self.visibilityButton setTitle:@"◉" forState:UIControlStateNormal];
        [self.visibilityButton setTitleColor:AndroidControlFill() forState:UIControlStateNormal];
        self.visibilityButton.titleLabel.font =
            [UIFont systemFontOfSize:22.0 weight:UIFontWeightRegular];
        self.visibilityButton.accessibilityLabel = @"Show or hide touch controls";
        [self.visibilityButton addTarget:self
                                  action:@selector(toggleControlsVisibility)
                        forControlEvents:UIControlEventTouchUpInside];
        [self addSubview:self.visibilityButton];
    }
    return self;
}

- (void)setRetunedFaceButtonLayout:(NSInteger)layout {
    self.faceButtonLayout = std::clamp<NSInteger>(layout, 0, 2);

    self.buttonA.controllerButton=kButtonA;
    self.buttonB.controllerButton=kButtonB;
    self.buttonX.controllerButton=kButtonX;
    self.buttonY.controllerButton=kButtonY;
    [self setNeedsLayout];
}

- (UIView*)hitTest:(CGPoint)point withEvent:(UIEvent*)event {
    UIView* hit = [super hitTest:point withEvent:event];
    if (hit == self || hit == self.controlGroup) {
        return nil;
    }
    return hit;
}

- (void)toggleControlsVisibility {
    self.controlsHiddenByUser = !self.controlsHiddenByUser;
    [self cancelAllInputs];
    RetunedTouchSetEnabled(!self.controlsHiddenByUser);
    [self applyVisibility];
}

- (void)applyVisibility {
    BOOL hideGameplayControls = self.controlsHiddenByUser;
    for (UIView* view in self.controlGroup.subviews) {
        view.hidden = hideGameplayControls;
    }
    self.buttonZL.hidden=hideGameplayControls || !self.extraShoulders;
    self.buttonZR.hidden=hideGameplayControls || !self.extraShoulders;
    self.buttonBack.hidden = hideGameplayControls;
    self.visibilityButton.hidden = NO;
}

- (void)setRetunedMenuVisible:(BOOL)visible {
    if (self.menuVisible == visible) {
        return;
    }
    self.menuVisible = visible;
    [self setNeedsLayout];
    [self cancelAllInputs];
    [self applyVisibility];
}

- (void)layoutSubviews {
    [super layoutSubviews];
    UIEdgeInsets safe = self.safeAreaInsets;
    CGFloat width = CGRectGetWidth(self.bounds);
    CGFloat height = CGRectGetHeight(self.bounds);
    BOOL isPad = UIDevice.currentDevice.userInterfaceIdiom == UIUserInterfaceIdiomPad;
    CGFloat maximumScale = isPad ? 1.35 : 1.15;
    CGFloat scale = self.controlScale * std::clamp(height / 390.0, 0.82, maximumScale);
    CGFloat left = safe.left + 16.0 * scale;
    CGFloat right = safe.right + 16.0 * scale;
    CGFloat top = safe.top + 16.0 * scale;
    CGFloat bottom = safe.bottom + 16.0 * scale;

    CGFloat shoulderWidth = 84.0 * scale;
    CGFloat shoulderHeight = 46.0 * scale;
    CGFloat shoulderGap = 10.0 * scale;
    self.buttonZL.frame = CGRectMake(left, top, shoulderWidth, shoulderHeight);
    self.buttonL.frame =
        CGRectMake(left, (self.extraShoulders?CGRectGetMaxY(self.buttonZL.frame) + shoulderGap:top),
                   shoulderWidth, shoulderHeight);
    self.buttonZR.frame =
        CGRectMake(width - right - shoulderWidth, top, shoulderWidth, shoulderHeight);
    self.buttonR.frame =
        CGRectMake(width - right - shoulderWidth,
                   (self.extraShoulders?CGRectGetMaxY(self.buttonZR.frame) + shoulderGap:top),
                   shoulderWidth, shoulderHeight);

    CGFloat stickSize = 150.0 * scale;
    self.leftStick.stickDiameter = stickSize;
    self.leftStick.frame = CGRectMake(0.0, 0.0, width * 0.46, height);
    if(self.menuVisible)self.leftStick.frame=CGRectMake(left,height-bottom-stickSize,stickSize,stickSize);
    CGFloat rightStickSize = 132.0 * scale;
    self.rightStick.stickDiameter = rightStickSize;
    CGFloat rightStickStart = width * 0.52;
    self.rightStick.frame =
        CGRectMake(rightStickStart, 0.0, width - rightStickStart, height);

    self.rightStick.userInteractionEnabled=!self.menuVisible;
    CGFloat crossSize = 96.0 * scale;
    self.cCross.frame =
        CGRectMake(left + (stickSize - crossSize) * 0.5 - 30.0 * scale,
                   MAX(CGRectGetMaxY(self.buttonL.frame)+12.0*scale,height - bottom - stickSize - crossSize - 6.0 * scale),
                   crossSize, crossSize);

    CGFloat cHit = 30.0 * scale;
    CGFloat crossMidX = CGRectGetMidX(self.cCross.frame);
    CGFloat crossMidY = CGRectGetMidY(self.cCross.frame);
    self.cButtons[0].frame =
        CGRectMake(crossMidX - cHit * 0.5, CGRectGetMinY(self.cCross.frame), cHit, cHit);
    self.cButtons[1].frame =
        CGRectMake(crossMidX - cHit * 0.5, CGRectGetMaxY(self.cCross.frame) - cHit, cHit, cHit);
    self.cButtons[2].frame =
        CGRectMake(CGRectGetMinX(self.cCross.frame), crossMidY - cHit * 0.5, cHit, cHit);
    self.cButtons[3].frame =
        CGRectMake(CGRectGetMaxX(self.cCross.frame) - cHit, crossMidY - cHit * 0.5, cHit, cHit);

    CGFloat faceSize = 44.0 * scale;
    CGFloat faceOffset = 44.0 * scale;
    CGFloat faceCenterX = width - right - faceSize - faceOffset;
    CGFloat faceCenterY = height - bottom - faceSize - faceOffset;
    for (RetunedTouchButton* button in
         @[ self.buttonA, self.buttonB, self.buttonX, self.buttonY ]) {
        button.bounds = CGRectMake(0.0, 0.0, faceSize, faceSize);
    }
    if (self.faceButtonLayout == 0) {
        // Nintendo: X top, Y left, A right, B bottom.
        self.buttonX.center = CGPointMake(faceCenterX, faceCenterY - faceOffset);
        self.buttonY.center = CGPointMake(faceCenterX - faceOffset, faceCenterY);
        self.buttonA.center = CGPointMake(faceCenterX + faceOffset, faceCenterY);
        self.buttonB.center = CGPointMake(faceCenterX, faceCenterY + faceOffset);
    } else if (self.faceButtonLayout == 2) {
        // GameCube: prominent A, B lower-left, X upper-right, Y upper-center.
        self.buttonA.bounds = CGRectMake(0.0, 0.0, faceSize * 1.35, faceSize * 1.35);
        self.buttonA.center = CGPointMake(faceCenterX + 12.0 * scale,
                                          faceCenterY + 20.0 * scale);
        self.buttonB.center = CGPointMake(faceCenterX - faceOffset,
                                          faceCenterY + faceOffset * 0.65);
        self.buttonX.center = CGPointMake(faceCenterX + faceOffset,
                                          faceCenterY - faceOffset * 0.55);
        self.buttonY.center = CGPointMake(faceCenterX - 8.0 * scale,
                                          faceCenterY - faceOffset);
    } else {
        // Xbox: Y top, X left, B right, A bottom.
        self.buttonY.center = CGPointMake(faceCenterX, faceCenterY - faceOffset);
        self.buttonX.center = CGPointMake(faceCenterX - faceOffset, faceCenterY);
        self.buttonB.center = CGPointMake(faceCenterX + faceOffset, faceCenterY);
        self.buttonA.center = CGPointMake(faceCenterX, faceCenterY + faceOffset);
    }

    CGFloat centerX = CGRectGetMidX(self.bounds);
    CGFloat systemWidth = 76.0 * scale;
    CGFloat systemHeight = 30.0 * scale;
    self.buttonBack.frame =
        CGRectMake(centerX - 100.0 * scale - systemWidth * 0.5,
                   height - safe.bottom - systemHeight - 10.0 * scale,
                   systemWidth, systemHeight);
    self.buttonStart.frame =
        CGRectMake(centerX + 100.0 * scale - systemWidth * 0.5,
                   height - safe.bottom - systemHeight - 10.0 * scale,
                   systemWidth, systemHeight);

    CGFloat toggleSize = 30.0 * scale;
    self.visibilityButton.frame =
        CGRectMake(width - safe.right - toggleSize - 10.0 * scale,
                   height - safe.bottom - toggleSize - 10.0 * scale,
                   toggleSize, toggleSize);

    [self.controlGroup sendSubviewToBack:self.rightStick];
    [self.controlGroup sendSubviewToBack:self.leftStick];
    RetunedTouchSetHudDisplay(width,height);
    for(unsigned slot=0;slot<8;++slot) {
        UIView* view=slot<4?@[self.buttonA,self.buttonB,self.buttonX,self.buttonY][slot]:self.cButtons[slot-4];
        const CGPoint center=[view.superview convertPoint:view.center toView:self];
        RetunedTouchSetHudAnchor(slot,center.x/width,center.y/height);
    }
    [self applyVisibility];
}

- (void)cancelAllInputs {
    [self.leftStick cancelInput];
    [self.rightStick cancelInput];
    for (RetunedTouchButton* button in self.allInputButtons) {
        [button cancelInput];
    }
}

@end

static RetunedTouchOverlay* sTouchOverlay;
static BOOL sTouchControlsDesired;
static NSInteger sTouchFaceButtonLayout;
static BOOL sTouchLeftStickFloating = YES;
static std::atomic_int sTouchControlsMenuVisible(1);
static float sTouchControlScale=1.f;

static UIWindow* ActiveWindow() {
    for (UIScene* scene in UIApplication.sharedApplication.connectedScenes) {
        if (![scene isKindOfClass:UIWindowScene.class]) {
            continue;
        }
        for (UIWindow* window in ((UIWindowScene*)scene).windows) {
            if (window.isKeyWindow) {
                return window;
            }
        }
    }
    return UIApplication.sharedApplication.windows.firstObject;
}

static void ApplyTouchControlsState() {
    UIWindow* window = ActiveWindow();
    if (window == nil) {
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.25 * NSEC_PER_SEC)),
                       dispatch_get_main_queue(), ^{
                           ApplyTouchControlsState();
                       });
        return;
    }

    if (!sTouchControlsDesired) {
        [sTouchOverlay cancelAllInputs];
        [sTouchOverlay removeFromSuperview];
        sTouchOverlay = nil;
        return;
    }

    if (sTouchOverlay == nil) {
        sTouchOverlay = [[RetunedTouchOverlay alloc] initWithFrame:window.bounds];
        sTouchOverlay.autoresizingMask =
            UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    }
    [sTouchOverlay setRetunedFaceButtonLayout:sTouchFaceButtonLayout];
    sTouchOverlay.leftStick.floating = sTouchLeftStickFloating;
    sTouchOverlay.controlScale=sTouchControlScale;
    [sTouchOverlay setNeedsLayout];
    if (sTouchOverlay.superview != window) {
        [sTouchOverlay removeFromSuperview];
        sTouchOverlay.frame = window.bounds;
        [window addSubview:sTouchOverlay];
    }
    [sTouchOverlay setRetunedMenuVisible:sTouchControlsMenuVisible.load()!=0];
    sTouchOverlay.hidden=sTouchControlsMenuVisible.load()!=0;
    [window bringSubviewToFront:sTouchOverlay];
}

int RetunedIOS_TouchControlsAvailable(void) {
    return 1;
}

void RetunedIOS_SetTouchControlsEnabled(int enabled) {
    dispatch_async(dispatch_get_main_queue(), ^{
        sTouchControlsDesired = YES;
        ApplyTouchControlsState();
        sTouchOverlay.controlsHiddenByUser = enabled == 0;
        [sTouchOverlay applyVisibility];
    });
}

void RetunedIOS_SetFaceButtonLayout(int layout) {
    dispatch_async(dispatch_get_main_queue(), ^{
        sTouchFaceButtonLayout = std::clamp(layout, 0, 2);
        [sTouchOverlay setRetunedFaceButtonLayout:sTouchFaceButtonLayout];
    });
}

void RetunedIOS_SetTouchLeftStickFloating(int floating) {
    dispatch_async(dispatch_get_main_queue(), ^{
        sTouchLeftStickFloating = floating != 0;
        sTouchOverlay.leftStick.floating = sTouchLeftStickFloating;
    sTouchOverlay.controlScale=sTouchControlScale;
    });
}

void RetunedIOS_SetTouchControlsMenuVisible(int visible) {
    if(sTouchControlsMenuVisible.exchange(visible)==visible)return;
    dispatch_async(dispatch_get_main_queue(), ^{
        ApplyTouchControlsState();
    });
}


void RetunedIOS_SetTouchOpacity(float opacity) {
    dispatch_async(dispatch_get_main_queue(), ^{
        sArtworkOpacity=std::clamp(opacity,.1f,.75f);
        if(!sTouchOverlay)return;
        for(RetunedTouchButton* button in sTouchOverlay.allInputButtons) {
            [button setTitleColor:AndroidControlStroke() forState:UIControlStateNormal];
            [button setNeedsLayout];
        }
        for(RetunedTouchStick* stick in @[sTouchOverlay.leftStick,sTouchOverlay.rightStick]) {
            stick.base.layer.borderColor=AndroidControlStroke().CGColor;
            stick.knob.layer.borderColor=AndroidControlStroke().CGColor;
            stick.knob.backgroundColor=AndroidControlFill();
        }
        [sTouchOverlay.cCross setNeedsDisplay];
    });
}

void RetunedIOS_SetTouchScale(float scale) {
    dispatch_async(dispatch_get_main_queue(), ^{
        sTouchControlScale=std::clamp(scale,.75f,1.25f);
        [sTouchOverlay cancelAllInputs];
        sTouchOverlay.controlScale=sTouchControlScale;
        [sTouchOverlay setNeedsLayout];
    });
}

void RetunedIOS_SetExtraShoulders(int enabled) {
    dispatch_async(dispatch_get_main_queue(), ^{
        [sTouchOverlay cancelAllInputs];
        sTouchOverlay.extraShoulders=enabled!=0;
        [sTouchOverlay setNeedsLayout];
        [sTouchOverlay applyVisibility];
    });
}

void RetunedIOS_SetTouchHudIcons(int enabled) {
    dispatch_async(dispatch_get_main_queue(), ^{
        if(!sTouchOverlay)return;
        sTouchOverlay.cCross.hudIcons=enabled!=0;
        [sTouchOverlay.cCross setNeedsDisplay];
        for(RetunedTouchButton* button in @[sTouchOverlay.buttonA,sTouchOverlay.buttonB,sTouchOverlay.buttonX,sTouchOverlay.buttonY]){
            button.hudIcon=enabled!=0;[button setNeedsLayout];
        }
    });
}
