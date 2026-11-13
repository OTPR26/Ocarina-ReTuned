#include "three_ds_motion_composition.h"
#include <cmath>
#include <stdexcept>
using namespace ThreeDsRecomp::Input;
static void near(float actual,float expected) {
    if(std::abs(actual-expected)>0.001f)throw std::runtime_error("motion axis changed after stick turning");
}
int main() {
    for(int hz:{30,60,90,120}) for(float turn:{-360.f,-90.f,-45.f,0.f,45.f,90.f,360.f}) {
        MotionCompositionState state;
        for(int i=0;i<hz;i++) {
            auto frame=state.Sample({0,-1,0},true,{},0,turn,1.0/hz,true,true);
            near(frame.AngularVelocity[1],turn);
            near(frame.Gravity[0],0);near(frame.Gravity[1],-1);near(frame.Gravity[2],0);
        }
        for(float pitch:{-60.f,60.f}) {
            auto frame=state.Sample({0,-1,0},true,{pitch,0,0},0,0,1.0/hz,true,true);
            near(frame.AngularVelocity[0],pitch);
            near(frame.AngularVelocity[1],0);near(frame.AngularVelocity[2],0);
        }
        // Virtual elevation still persists, and yaw follows the tilted gravity.
        for(int i=0;i<hz;i++)state.Sample({0,-1,0},true,{},60,turn,1.0/hz,true,true);
        auto frame=state.Sample({0,-1,0},true,{60,0,0},0,0,1.0/hz,true,true);
        near(frame.AngularVelocity[0],60);near(frame.AngularVelocity[1],0);near(frame.AngularVelocity[2],0);
        near(frame.Gravity[1],-0.5f);near(frame.Gravity[2],0.8660254f);
    }
}
