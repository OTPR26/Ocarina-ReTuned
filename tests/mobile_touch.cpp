#include "../tools/frontend/touch_model.h"
#include "../tools/frontend/responsive_layout.h"
#include <cassert>
using namespace RetunedFrontend;
int main(){
 NativeTouchState native;
 native.Button(TouchAction::A,true);native.Button(TouchAction::A,false);
 assert(native.Sample(true).Buttons&(uint32_t{1}<<unsigned(TouchAction::A)));
 assert(!native.Sample(true).Buttons);
 native.MoveX=.5f;native.Button(TouchAction::Shield,true);assert(native.Sample(true).MoveX==.5f);
 native.Reset();assert(!native.Sample(true).Captured);
 assert(ExtraShoulderAction(false,static_cast<int>(TouchAction::A))==-1);
 assert(ExtraShoulderAction(true,-1)==-1);
 assert(ExtraShoulderAction(true,static_cast<int>(TouchAction::Settings))==-1);
 assert(ExtraShoulderAction(true,static_cast<int>(TouchAction::Y))==static_cast<int>(TouchAction::Y));
 native.SourceButton(0,TouchAction::A,true);native.SourceButton(104,TouchAction::A,true);
 native.Sample(true);native.SourceButton(104,TouchAction::A,false);
 assert(native.Sample(true).Buttons&TouchModel::Bit(TouchAction::A));
 native.SourceButton(0,TouchAction::A,false);assert(native.Sample(true).Buttons==0);
 native.Reset();
 TouchModel m;m.SetAspect(16.f/9);
 m.Down(1,.16f,.72f);m.Motion(1,.20f,.69f);m.Down(2,.91f,.70f);
 auto s=m.Sample(true);assert(s.MoveX>0&&s.MoveY>0&&(s.Buttons&TouchModel::Bit(TouchAction::A)));
 m.Up(2);s=m.Sample(true);assert(s.MoveX>0&&s.Buttons==0);
 m.Down(3,.82f,.81f);m.Up(3);assert(m.Sample(false).Buttons&TouchModel::Bit(TouchAction::B));
 assert(m.Sample(true).Buttons&TouchModel::Bit(TouchAction::B));assert(m.Sample(true).Buttons==0);
 m.Down(4,.65f,.72f);m.Motion(4,.99f,.99f);s=m.Sample(false);assert(std::hypot(s.LookX,s.LookY)<=1.0001f);
 m.Reset();s=m.Sample(true);assert(!s.Captured&&s.MoveX==0&&s.MoveY==0&&s.Buttons==0);
 m.Down(5,.91f,.70f,false);assert(!m.Sample(true).Captured);
 m.Down(6,.56f,.90f,false);assert(m.Sample(true).Buttons&TouchModel::Bit(TouchAction::Settings));
 m.Reset();m.Down(7,.16f,.72f);m.Down(8,.16f,.72f);m.Up(7);assert(!m.Sample(true).Captured);
 assert(InterfaceScale(440)==.75f&&InterfaceScale(720)==1.f&&InterfaceScale(1080)==1.5f);
 SetInterfacePixelRatio(956,2868);assert(InterfacePixelRatio==3.f);
 assert(InterfaceFontPixels()==192.f);assert(std::abs(InterfaceFontPixels()*InterfaceFontScale()-20.f)<.001f);
 SetInterfacePixelRatio(1920,3840);assert(InterfacePixelRatio==2.f);
 assert(std::abs(InterfaceFontPixels()*InterfaceFontScale(1.5f)-30.f)<.001f);
 SetInterfacePixelRatio(0,0);assert(InterfacePixelRatio==1.f);
 assert(NavigationWidth(700,15)<700*.3f);
}
