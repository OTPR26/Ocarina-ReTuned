#include "../tools/frontend/mobile_device_motion.h"
#include <cassert>
#include <cmath>
#include <limits>
using ThreeDsRecomp::Input::MotionObservation;
int main(){
    constexpr float degrees=57.2957795f;
    auto near=[](float a,float b){assert(std::abs(a-b)<0.001f);};
    {
        RetunedFrontend::MobileDeviceMotion device;
        MotionObservation sample;
        device.Sample(sample,true);
        assert(sample.GyroscopeValid && sample.AccelerometerValid && FakeMotion::open==2);
        near(sample.GyroscopeDegreesPerSecond[0],-degrees);
        near(sample.GyroscopeDegreesPerSecond[1],2*degrees);
        near(sample.Accelerometer[1],-1);
        FakeMotion::orientation=SDL_ORIENTATION_LANDSCAPE;
        sample={};device.Sample(sample,true);
        near(sample.GyroscopeDegreesPerSecond[0],2*degrees);
        near(sample.GyroscopeDegreesPerSecond[1],degrees);
        FakeMotion::orientation=SDL_ORIENTATION_LANDSCAPE_FLIPPED;
        sample={};device.Sample(sample,true);
        near(sample.GyroscopeDegreesPerSecond[0],-2*degrees);
        near(sample.GyroscopeDegreesPerSecond[1],-degrees);
        FakeMotion::orientation=SDL_ORIENTATION_PORTRAIT_FLIPPED;
        sample={};device.Sample(sample,true);
        near(sample.GyroscopeDegreesPerSecond[0],degrees);
        near(sample.GyroscopeDegreesPerSecond[1],-2*degrees);
        sample.GyroscopeDegreesPerSecond={7,8,9};sample.GyroscopeValid=true;
        device.Sample(sample,true);
        assert(sample.GyroscopeDegreesPerSecond[0]==7 && FakeMotion::open==0);
        sample={};device.Sample(sample,false);assert(!sample.GyroscopeValid && FakeMotion::open==0);
        device.Sample(sample,true);assert(FakeMotion::open==2);
        FakeMotion::Send(SDL_APP_WILLENTERBACKGROUND);assert(FakeMotion::open==0);
        sample={};device.Sample(sample,true);assert(!sample.GyroscopeValid);
        FakeMotion::Send(SDL_APP_DIDENTERFOREGROUND);
        device.Sample(sample,true);assert(sample.GyroscopeValid && FakeMotion::open==2);
        FakeMotion::sensors[1].fail=true;
        sample={};device.Sample(sample,true);assert(!sample.GyroscopeValid && sample.AccelerometerValid);
        FakeMotion::sensors[1].fail=false;
        FakeMotion::sensors[1].data[0]=std::numeric_limits<float>::quiet_NaN();
        sample={};device.Sample(sample,true);assert(!sample.GyroscopeValid);
        FakeMotion::Send(SDL_APP_TERMINATING);assert(FakeMotion::open==0);
    }
    assert(FakeMotion::watches.empty() && FakeMotion::open==0);
    FakeMotion::count=0;
    {RetunedFrontend::MobileDeviceMotion absent;MotionObservation sample;absent.Sample(sample,true);assert(!sample.GyroscopeValid);}
    assert(FakeMotion::watches.empty());
}
