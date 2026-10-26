// SPDX-License-Identifier: GPL-2.0-or-later
#import "duo_equipment_strip.h"
#include "fast/oot3d/retuned_screen_probe.h"
#include "fast/oot3d/lower_equipment_state.h"
using namespace RetunedFrontend;
@implementation RetunedDuoEquipmentStrip {
    UIImage* _stone; UIImage* _skin; UIImage* _agony;
    UIImage* _boots[3]; UIImage* _tunics[3];
    unsigned _snapshot; NSInteger _pressed; CGRect _cells[3];
}
- (UIImage*)art:(NSString*)name {
    NSString* relative=[@"lower-equipment" stringByAppendingPathComponent:[name stringByAppendingString:@".png"]];
    NSString* data=[NSSearchPathForDirectoriesInDomains(NSApplicationSupportDirectory,NSUserDomainMask,YES).firstObject stringByAppendingPathComponent:@"OcarinaReTuned"];
    UIImage* image=[UIImage imageWithContentsOfFile:[data stringByAppendingPathComponent:relative]];
    if(!image)image=[UIImage imageWithContentsOfFile:[[NSBundle.mainBundle.bundlePath stringByAppendingPathComponent:@"PrivateGame"] stringByAppendingPathComponent:relative]];
    return image;
}
- (instancetype)initWithFrame:(CGRect)frame {
    if(!(self=[super initWithFrame:frame]))return nil;
    self.backgroundColor=UIColor.clearColor; self.opaque=NO; _pressed=-1;
    _stone=[self art:@"stone"]; _skin=[self art:@"button"]; _agony=[self art:@"agony"];
    for(int i=0;i<3;i++) {
        _boots[i]=[self art:[NSString stringWithFormat:@"boots-%d",i+1]];
        _tunics[i]=[self art:[NSString stringWithFormat:@"tunic-%d",i+1]];
    }
    self.accessibilityLabel=@"Quick boots, tunic, and Shard of Agony";
    return self;
}
- (BOOL)enabled:(int)n {
    const unsigned owned=(_snapshot>>(n==0?8:11))&7;
    return (_snapshot&1)&&n<2&&(__builtin_popcount(owned)+(n==0&&!(owned&1)?1:0)>1);
}
- (void)refresh {
    UIView* parent=self.superview;
    const auto pane=DuoDisplay.LowerPanelBounds(parent.bounds.size.width,parent.bounds.size.height,ProbeGuestDualActive.load());
    const auto picture=DuoDisplay.Layout(parent.bounds.size.width,parent.bounds.size.height,ProbeGuestDualActive.load()).Lower;
    const float y=picture.Y+picture.Height,h=pane.Y+pane.Height-y;
    const CGFloat scale=parent.window.screen.nativeScale;
    LowerEquipmentSurfaceWidth=picture.Width>0?unsigned(std::lround(picture.Width*scale)):0;
    LowerEquipmentSurfaceHeight=picture.Height>0?unsigned(std::lround(picture.Height*scale)):0;
    _snapshot=LowerEquipmentState.load();
    self.hidden=!LowerEquipmentPanelEnabled.load()||!ProbeGuestDualActive.load()||
        h<24||!(_snapshot&(1u<<14))||!_stone||!_skin;
    if(self.hidden){_pressed=-1;return;}
    self.frame=CGRectMake(pane.X,y,pane.Width,h);
    [self setNeedsDisplay];
}
- (void)drawRect:(CGRect)rect {
    const CGFloat w=self.bounds.size.width,h=self.bounds.size.height;
    [_stone drawInRect:self.bounds];
    const CGFloat bevel=MIN(1.0,h*.02);
    [[UIColor colorWithWhite:0 alpha:90.0/255]setFill];UIRectFill(CGRectMake(0,0,w,bevel));
    [[UIColor colorWithWhite:1 alpha:40.0/255]setFill];UIRectFill(CGRectMake(0,bevel,w,1.0/MAX(1.0,self.contentScaleFactor)));
    const CGFloat cell=MIN(w/3,h*1.65),start=(w-cell*3)/2,edge=h*.9;
    for(int n=0;n<3;n++) {
        _cells[n]=CGRectMake(start+n*cell,0,cell,h);
        if(n==2&&!(_snapshot&2))continue;
        CGRect button=CGRectMake(CGRectGetMidX(_cells[n])-edge/2,(h-edge)/2,edge,edge);
        [_skin drawInRect:button];
        const unsigned member=(_snapshot>>(n==0?4:6))&3;
        const unsigned index=member?MIN(2u,member-1):0;
        UIImage* image=n==2?_agony:(n==0?_boots[index]:_tunics[index]);
        const BOOL active=n==2?(_snapshot&4)!=0:[self enabled:n];
        [image drawInRect:CGRectInset(button,edge*.15,edge*.15) blendMode:kCGBlendModeNormal alpha:active?1:(n==2?185.0/255:130.0/255)];
        if(n==2&&active) {
            [[UIColor colorWithRed:160.0/255 green:235.0/255 blue:1 alpha:1]setStroke];
            UIBezierPath* path=[UIBezierPath bezierPathWithRoundedRect:button cornerRadius:10/MAX(1.0,self.contentScaleFactor)];
            path.lineWidth=3/MAX(1.0,self.contentScaleFactor);[path stroke];
        }
    }
}
- (void)touchesBegan:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event {
    _pressed=-1;CGPoint point=[touches.anyObject locationInView:self];
    for(int n=0;n<2;n++)if(CGRectContainsPoint(_cells[n],point)&&[self enabled:n])_pressed=n;
}
- (void)touchesEnded:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event {
    CGPoint point=[touches.anyObject locationInView:self];
    if(_pressed>=0&&CGRectContainsPoint(_cells[_pressed],point)&&[self enabled:(int)_pressed])
        LowerEquipmentRequest=unsigned(_pressed+1);
    _pressed=-1;
}
- (void)touchesCancelled:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event {_pressed=-1;}
@end
