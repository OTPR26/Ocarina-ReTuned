#include "oot3d_native_frame_rate.h"
#include <cassert>
#include <cmath>
int main(){
    using namespace Oot3dNativeGame;
    NativePresentationScheduler scheduler(30,NativeSimulationCatchUpPolicy::PreserveBoundedDebt,4);
    scheduler.Advance(0);
    double elapsed=0;uint64_t refreshes=0;
    // Regular 30 Hz presentation with periodic 50 ms stalls and compensating short frames.
    for(int i=0;i<10000;++i){
        const double dt=i%10==0?0.05:i%10==1?1.0/60.0:1.0/30.0;
        elapsed+=dt;auto step=scheduler.Advance(dt);refreshes+=step.GuestRefreshesDue;
        assert(step.DroppedGuestRefreshes==0 && step.GuestRefreshesDue<=4);
    }
    assert(std::abs(double(refreshes)-elapsed*60)<1.01);
    const auto stall=scheduler.Advance(2.0);
    assert(stall.GuestRefreshesDue==4 && stall.DeferredGuestRefreshes==8 && stall.DroppedGuestRefreshes==108);
    const auto resume=scheduler.Advance(1.0/30.0);
    assert(resume.GuestRefreshesDue==4 && resume.DeferredGuestRefreshes==6);
}
