#include "runtime_services.h"
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <chrono>
using namespace RetunedRandomizer;
void Check(bool value) {if(!value)throw std::runtime_error("Check failed");}
template<class F> void Reject(F f) {bool rejected=false;try{f();}catch(const std::exception&){rejected=true;}Check(rejected);}
int main() {
    const auto root=std::filesystem::temp_directory_path()/("retuned-seed-test-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    std::filesystem::create_directory(root);
    struct Cleanup {std::filesystem::path path;~Cleanup(){std::filesystem::remove_all(path);}} cleanup{root};
    SaveStore store(root/"profile",std::string(64,'a'),std::string(64,'b'),16,true);
    Bytes native(0x14dc,1),ext(16,2),next=native;next[100]=3;
    store.BeforeWrite(0,native,ext);
    Check(store.Load(0,native)==ext);
    // Durable orphan for a failed native write must not disturb old state.
    store.BeforeWrite(0,next,Bytes(16,4));
    Check(store.Load(0,native)==ext);
    SaveStore reopened(root/"profile",std::string(64,'a'),std::string(64,'b'),16,false);
    Check(reopened.Load(0,next)==Bytes(16,4));
    Reject([&]{store.BeforeWrite(0,native,Bytes(16,9));});
    Reject([&]{store.Load(1,native);});
    Reject([&]{SaveStore wrong(root/"profile",std::string(64,'c'),std::string(64,'b'),16,false);});
    Reject([&]{store.BeforeWrite(3,native,ext);});
    Reject([&]{store.BeforeWrite(0,Bytes(2),ext);});
    Bytes memory(0x800000);
    GuestMemory guest{
        [&](auto at,auto size){
            // Match native-host regions: a bulk read cannot cross rodata/data.
            Check((at>=0x4f9000 && at+size<=0x5c7000) ||
                  (at>=0x680000 && at+size<=0x800000));
            return Bytes(memory.begin()+at,memory.begin()+at+size);
        },
        [&](auto at,auto bytes){std::copy(bytes.begin(),bytes.end(),memory.begin()+at);}};
    RuntimeServices services(store,guest,0x700000,16,[&](unsigned){return native;});
    std::array<std::uint32_t,16> r{};
    Check(!services.Handle(0x123,r));
    Reject([&]{services.CommitNativeWrite(0,0,native);});
    services.Handle(0xfff403,r);
    Check(Bytes(memory.begin()+0x700000,memory.begin()+0x700010)==ext);
    services.Handle(0xfff404,r);
    services.Handle(0xfff404,r); // Post-write notifications may repeat.
    services.CommitNativeWrite(0,0,native);
    Check(std::filesystem::file_size(root/"profile/native/save00.bin")==native.size());
    // Capture the state at the actual native write, not an earlier notification.
    std::fill(memory.begin()+0x700000,memory.begin()+0x700010,4);
    services.CommitNativeWrite(0,0,next);
    Check(store.Load(0,next)==Bytes(16,4));
    // Copies use the already loaded source state with a different destination.
    services.CommitNativeWrite(1,0,next);
    Check(store.Load(1,next)==Bytes(16,4));
    Reject([&]{services.CommitNativeWrite(0,1,native);});
    Reject([&]{services.Handle(0xfff402,r);});
    memory[0x53cd78]=77; // Unchanged next object keeps its cached size.
    services.Handle(0xfff401,r);
    Reject([&]{services.Handle(0xfff401,r);});
    memory[0x53ccf4]=1;memory[0x53cd34]=99;
    memory[0x53ccf4+0x1a0*0x44]=2;
    memory[0x53ccf4+0x1a0*0x44+0x40]=66;
    services.Handle(0xfff402,r);Check(memory[0x53cd34]==0);
    Check(memory[0x53cd78]==77);
    Check(memory[0x53ccf4+0x1a0*0x44+0x40]==0);
    r[0]=55;services.Handle(0xfff405,r);Check(r[0]==55);
    services.Handle(0xfff40b,r);Check(r[0]==2);
    // Interrupted temporary files are ignored, never mistaken for committed state.
    std::ofstream(root/"profile/native/save00.bin.partial-1")<<"interrupted";
    store.Commit(0,next,Bytes(16,4));
    Check(store.Load(0,next)==Bytes(16,4));
    // A destination failure leaves the previous native bytes intact.
    SaveStore blocked(root/"blocked",std::string(64,'a'),std::string(64,'b'),16,true);
    std::ofstream(root/"blocked/native")<<"not a directory";
    Reject([&]{blocked.Commit(0,native,ext);});
    Check(blocked.Load(0,native)==ext); // durable orphan can be retried
    // Corruption must be rejected rather than silently resetting progress.
    for(const auto& entry:std::filesystem::directory_iterator(root/"profile")) {
        if(entry.path().extension()==".state") {
            std::fstream f(entry.path(),std::ios::binary|std::ios::in|std::ios::out);
            f.put('X');
        }
    }
    Reject([&]{store.Load(0,native);});
    std::cout<<"Save identity, restart, interrupted writes, corruption, and all six services passed\n";
}
