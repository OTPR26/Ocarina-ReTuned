// Included after RetunedTouchOverlay's declaration; gameplay views never receive editor gestures.
@interface RetunedTouchLayoutEditor : UIView <UIGestureRecognizerDelegate>
@property(nonatomic, weak) RetunedTouchOverlay* owner;
@property(nonatomic, strong) NSMutableDictionary<NSString*, UILabel*>* handles;
@property(nonatomic, strong) NSArray<UIButton*>* actions;
@property(nonatomic, strong) UILabel* instruction;
@property(nonatomic, copy) NSString* selected;
@property(nonatomic) CGFloat pinchStartSize;
- (instancetype)initWithOwner:(RetunedTouchOverlay*)owner;
@end

@implementation RetunedTouchLayoutEditor
- (instancetype)initWithOwner:(RetunedTouchOverlay*)owner {
    if(!(self=[super initWithFrame:owner.bounds]))return nil;
    self.owner=owner;self.autoresizingMask=UIViewAutoresizingFlexibleWidth|UIViewAutoresizingFlexibleHeight;
    self.backgroundColor=[UIColor colorWithRed:.03 green:.035 blue:.06 alpha:.95];
    self.accessibilityLabel=@"Touch layout editor";
    self.handles=[NSMutableDictionary dictionary];
    for(NSString* key in [owner placementControls]) {
        UILabel* label=[UILabel new];label.text=key;label.accessibilityIdentifier=key;label.numberOfLines=2;label.textAlignment=NSTextAlignmentCenter;
        label.textColor=UIColor.whiteColor;label.layer.borderColor=UIColor.whiteColor.CGColor;
        label.layer.borderWidth=1.5;label.adjustsFontSizeToFitWidth=YES;label.minimumScaleFactor=.55;
        label.userInteractionEnabled=YES;label.accessibilityLabel=[@"Move " stringByAppendingString:key];
        UIPanGestureRecognizer* pan=[[UIPanGestureRecognizer alloc] initWithTarget:self action:@selector(moveControl:)];
        pan.delegate=self;pan.maximumNumberOfTouches=1;[label addGestureRecognizer:pan];
        [label addGestureRecognizer:[[UITapGestureRecognizer alloc] initWithTarget:self action:@selector(selectControl:)]];
        self.handles[key]=label;[self addSubview:label];
    }
    NSMutableArray* actions=[NSMutableArray array];
    for(NSString* text in @[@"Save",@"Cancel",@"Reset"]) {
        UIButton* button=[UIButton buttonWithType:UIButtonTypeSystem];
        [button setTitle:text forState:UIControlStateNormal];[button setTitleColor:UIColor.whiteColor forState:UIControlStateNormal];
        button.backgroundColor=[UIColor colorWithRed:.14 green:.21 blue:.28 alpha:1];button.layer.cornerRadius=6;
        [button addTarget:self action:@selector(action:) forControlEvents:UIControlEventTouchUpInside];
        [actions addObject:button];[self addSubview:button];
    }
    UIPinchGestureRecognizer* pinch=[[UIPinchGestureRecognizer alloc] initWithTarget:self action:@selector(resizeControl:)];
    pinch.delegate=self;[self addGestureRecognizer:pinch];
    self.actions=actions;self.instruction=[UILabel new];self.instruction.textAlignment=NSTextAlignmentCenter;
    self.instruction.textColor=UIColor.whiteColor;self.instruction.adjustsFontSizeToFitWidth=YES;
    [self addSubview:self.instruction];
    [NSNotificationCenter.defaultCenter addObserver:self selector:@selector(cancel) name:UIApplicationWillResignActiveNotification object:nil];
    return self;
}
- (void)dealloc {[NSNotificationCenter.defaultCenter removeObserver:self];}
- (void)layoutSubviews {
    [super layoutSubviews];
    CGFloat scale=std::clamp(self.bounds.size.height/390.,.82,1.35);
    for(NSString* key in self.handles) {
        UILabel* handle=self.handles[key];handle.frame=[self.owner placementRect:key];
        BOOL round=[@[@"A",@"B",@"X",@"Y",@"Move",@"Look",@"Map",@"Eye"] containsObject:key];
        CGFloat radius=MIN(handle.bounds.size.width,handle.bounds.size.height)/2;
        handle.layer.cornerRadius=round?radius:MIN(8,radius);
        handle.font=[UIFont systemFontOfSize:14*scale weight:UIFontWeightMedium];
        BOOL selected=[key isEqual:self.selected];
        handle.layer.borderColor=(selected?UIColor.systemYellowColor:UIColor.whiteColor).CGColor;
        handle.text=selected?[NSString stringWithFormat:@"%@\n%.0f%%",key,[self.owner sizeForControl:key]*100]:key;
    }
    CGFloat width=82*scale,gap=8*scale,x=(self.bounds.size.width-3*width-2*gap)/2,y=self.safeAreaInsets.top+12;
    for(unsigned i=0;i<self.actions.count;++i) {
        UIButton* button=self.actions[i];button.frame=CGRectMake(x+i*(width+gap),y,width,34*scale);
        button.titleLabel.font=[UIFont systemFontOfSize:15*scale weight:UIFontWeightSemibold];
        [self bringSubviewToFront:button];
    }
    self.instruction.text=self.owner.dualLayout?@"Dual-screen · Drag to move · Pinch to resize":@"Single-screen · Drag to move · Pinch to resize";
    self.instruction.font=[UIFont systemFontOfSize:12*scale];
    self.instruction.frame=CGRectMake(x,y+38*scale,3*width+2*gap,22*scale);
}
- (void)moveControl:(UIPanGestureRecognizer*)gesture {
    if(self.pinchStartSize>0)return;
    UILabel* handle=(UILabel*)gesture.view;NSString* key=handle.accessibilityIdentifier;
    if(gesture.state==UIGestureRecognizerStateCancelled||gesture.state==UIGestureRecognizerStateFailed)return;
    self.selected=key;
    if(gesture.state==UIGestureRecognizerStateBegan)handle.layer.borderColor=UIColor.systemYellowColor.CGColor;
    CGPoint translation=[gesture translationInView:self];
    CGPoint center=CGPointMake(handle.center.x+translation.x,handle.center.y+translation.y);
    CGFloat width=self.bounds.size.width,height=self.bounds.size.height;
    if(width<=0||height<=0)return;
    self.owner.placements[key]=@[@(std::clamp(center.x/width,0.,1.)),@(std::clamp(center.y/height,0.,1.))];
    [gesture setTranslation:CGPointZero inView:self];
    [self.owner setNeedsLayout];[self.owner layoutIfNeeded];[self setNeedsLayout];[self layoutIfNeeded];
}
- (void)selectControl:(UITapGestureRecognizer*)gesture {
    self.selected=gesture.view.accessibilityIdentifier;[self setNeedsLayout];
}
- (BOOL)gestureRecognizer:(UIGestureRecognizer*)gesture shouldReceiveTouch:(UITouch*)touch {
    for(UIButton* button in self.actions)if([touch.view isDescendantOfView:button])return NO;
    return YES;
}
- (BOOL)gestureRecognizer:(UIGestureRecognizer*)gesture shouldRecognizeSimultaneouslyWithGestureRecognizer:(UIGestureRecognizer*)other {
    // A second finger can start resizing after a one-finger drag has begun.
    return ([gesture isKindOfClass:UIPinchGestureRecognizer.class] && [other isKindOfClass:UIPanGestureRecognizer.class]) ||
           ([other isKindOfClass:UIPinchGestureRecognizer.class] && [gesture isKindOfClass:UIPanGestureRecognizer.class]);
}
- (void)resizeControl:(UIPinchGestureRecognizer*)gesture {
    if(gesture.state==UIGestureRecognizerStateBegan){
        // Prefer buttons over the larger stick regions when controls overlap.
        NSMutableArray* keys=[ControlKeys() mutableCopy];[keys removeObject:@"Move"];[keys removeObject:@"Look"];
        [keys addObjectsFromArray:@[@"Move",@"Look"]];
        NSString* target=nil;
        for(NSString* key in keys){
            for(NSUInteger i=0;i<gesture.numberOfTouches;++i)if(CGRectContainsPoint(self.handles[key].frame,[gesture locationOfTouch:i inView:self])){target=key;break;}
            if(target)break;
        }
        if(target)self.selected=target;
        if(!self.selected)return;
        self.pinchStartSize=[self.owner sizeForControl:self.selected];
        CGRect rect=[self.owner placementRect:self.selected];
        if(self.bounds.size.width<=0||self.bounds.size.height<=0)return;
        self.owner.placements[self.selected]=@[@(CGRectGetMidX(rect)/self.bounds.size.width),@(CGRectGetMidY(rect)/self.bounds.size.height)];
    }
    if(!self.selected||self.pinchStartSize<=0)return;
    if(gesture.state==UIGestureRecognizerStateBegan||gesture.state==UIGestureRecognizerStateChanged){
        self.owner.sizes[self.selected]=@(std::clamp(self.pinchStartSize*gesture.scale,.5,1.5));
        [self.owner setNeedsLayout];[self.owner layoutIfNeeded];[self setNeedsLayout];[self layoutIfNeeded];
    }
    if(gesture.state==UIGestureRecognizerStateEnded||gesture.state==UIGestureRecognizerStateCancelled)self.pinchStartSize=0;
}
- (void)action:(UIButton*)button {
    NSString* action=[button titleForState:UIControlStateNormal];
    if([action isEqual:@"Reset"]){[self.owner.placements removeAllObjects];for(NSString* key in ControlKeys())self.owner.sizes[key]=@1;self.selected=nil;[self.owner setNeedsLayout];[self.owner layoutIfNeeded];[self setNeedsLayout];}
    else [self.owner finishLayoutEditing:[action isEqual:@"Save"]];
}
- (void)cancel {[self.owner finishLayoutEditing:NO];}
@end
