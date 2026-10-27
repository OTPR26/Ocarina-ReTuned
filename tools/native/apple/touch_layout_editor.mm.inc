// Included after RetunedTouchOverlay's declaration; gameplay views never receive editor gestures.
@interface RetunedTouchLayoutEditor : UIView
@property(nonatomic, weak) RetunedTouchOverlay* owner;
@property(nonatomic, strong) NSMutableDictionary<NSString*, UILabel*>* handles;
@property(nonatomic, strong) NSArray<UIButton*>* actions;
@property(nonatomic, strong) UILabel* instruction;
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
        UILabel* label=[UILabel new];label.text=key;label.textAlignment=NSTextAlignmentCenter;
        label.textColor=UIColor.whiteColor;label.layer.borderColor=UIColor.whiteColor.CGColor;
        label.layer.borderWidth=1.5;label.adjustsFontSizeToFitWidth=YES;label.minimumScaleFactor=.55;
        label.userInteractionEnabled=YES;label.accessibilityLabel=[@"Move " stringByAppendingString:key];
        [label addGestureRecognizer:[[UIPanGestureRecognizer alloc] initWithTarget:self action:@selector(moveControl:)]];
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
        handle.layer.cornerRadius=MIN(8,handle.bounds.size.height/2);
        handle.font=[UIFont systemFontOfSize:14*scale weight:UIFontWeightMedium];
    }
    CGFloat width=82*scale,gap=8*scale,x=(self.bounds.size.width-3*width-2*gap)/2,y=self.safeAreaInsets.top+12;
    for(unsigned i=0;i<self.actions.count;++i) {
        UIButton* button=self.actions[i];button.frame=CGRectMake(x+i*(width+gap),y,width,34*scale);
        button.titleLabel.font=[UIFont systemFontOfSize:15*scale weight:UIFontWeightSemibold];
        [self bringSubviewToFront:button];
    }
    self.instruction.text=self.owner.dualLayout?@"Dual-screen layout · Drag controls to move":@"Single-screen layout · Drag controls to move";
    self.instruction.font=[UIFont systemFontOfSize:12*scale];
    self.instruction.frame=CGRectMake(x,y+38*scale,3*width+2*gap,22*scale);
}
- (void)moveControl:(UIPanGestureRecognizer*)gesture {
    UILabel* handle=(UILabel*)gesture.view;NSString* key=handle.text;
    if(gesture.state==UIGestureRecognizerStateBegan)handle.layer.borderColor=UIColor.systemYellowColor.CGColor;
    CGPoint translation=[gesture translationInView:self];
    CGPoint center=CGPointMake(handle.center.x+translation.x,handle.center.y+translation.y);
    CGFloat width=self.bounds.size.width,height=self.bounds.size.height;
    if(width<=0||height<=0)return;
    self.owner.placements[key]=@[@(std::clamp(center.x/width,0.,1.)),@(std::clamp(center.y/height,0.,1.))];
    [gesture setTranslation:CGPointZero inView:self];
    [self.owner setNeedsLayout];[self.owner layoutIfNeeded];[self setNeedsLayout];[self layoutIfNeeded];
}
- (void)action:(UIButton*)button {
    NSString* action=[button titleForState:UIControlStateNormal];
    if([action isEqual:@"Reset"]){[self.owner.placements removeAllObjects];[self.owner setNeedsLayout];[self.owner layoutIfNeeded];[self setNeedsLayout];}
    else [self.owner finishLayoutEditing:[action isEqual:@"Save"]];
}
- (void)cancel {[self.owner finishLayoutEditing:NO];}
@end
