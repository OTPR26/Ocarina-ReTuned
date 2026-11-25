#include "seed_activation.h"
#include "generator.h"
#include "run_launcher.h"
#include <fstream>
#include <iostream>
#include <functional>
using namespace RetunedRandomizer;
using Json=nlohmann::json;
void Check(bool ok) {if(!ok)throw std::runtime_error("Seed activation check failed");}
void Reject(const std::function<void()>& run) {
    bool rejected=false;try{run();}catch(const std::exception&){rejected=true;}Check(rejected);
}
struct Memory {
    std::vector<std::uint8_t> bytes=std::vector<std::uint8_t>(0x800000);
    unsigned writes=0; bool mapped=true;
    bool ReadBytes(std::uint32_t at,std::span<std::uint8_t> out) {
        if(!mapped || at+out.size()>bytes.size())return false;
        std::copy_n(bytes.begin()+at,out.size(),out.begin());return true;
    }
    bool WriteBytes(std::uint32_t at,std::span<const std::uint8_t> in) {
        ++writes;std::copy(in.begin(),in.end(),bytes.begin()+at);return true;
    }
};
int main(int argc,char** argv) {
    if(argc==6 && std::string(argv[1])=="--restore") {
        const auto run=RunCatalog(argv[2]).Read(0);
        const auto inventory=RetainedRuntimeInventory(argv[3]);
        const auto restored=RestoreRunRuntime(run,inventory,argv[4],true);
        const auto checked=ResolveRunRuntime(restored.manifest,{restored.module},run.runtimeHash,run.seedHash,true);
        Check(checked.module==restored.module);
        Json manifest;std::ifstream(restored.manifest)>>manifest;
        for(const auto& [key,value]:manifest.at("source").items()) {
            if(!key.ends_with("_path"))continue;
            const std::filesystem::path path=value.get<std::string>();
            Check(path.is_absolute() && std::filesystem::is_regular_file(path));
        }
        Reject([&]{RestoreRunRuntime(run,{},argv[4],true);});
        auto wrong=run;wrong.runtimeHash=std::string(64,'0');
        Reject([&]{RestoreRunRuntime(wrong,inventory,argv[4],true);});
        Reject([&]{RestoreRunRuntime(run,inventory,argv[4],false);});
        std::ofstream(argv[5])<<Json{{"manifest",restored.manifest.string()},{"module",restored.module.string()}};
        return 0;
    }
    if(argc==6 && std::string(argv[1])=="--bind") {
        Json prepared;std::ifstream(argv[2])>>prepared;
        std::ifstream input(argv[3]);const std::string seed{std::istreambuf_iterator<char>(input),{}};
        const auto run=BindSeedToRuntime({prepared.at("manifest").get<std::string>(),
            prepared.at("module").get<std::string>()},seed,argv[4],true);
        const auto repeated=BindSeedToRuntime({prepared.at("manifest").get<std::string>(),
            prepared.at("module").get<std::string>()},seed,argv[4],true);
        Check(run.manifest==repeated.manifest && run.module==repeated.module);
        std::ofstream(argv[5])<<Json{{"manifest",run.manifest.string()},{"module",run.module.string()}};
        return 0;
    }
    if(argc==4) {
        Json manifest,seed;std::ifstream(argv[1])>>manifest;std::ifstream(argv[2])>>seed;
        const auto writes=PlanSeedActivation(seed,manifest.at("randomizer_proof").at("seed_layout"));
        Json output=Json::array();
        for(const auto& w:writes)output.push_back({{"address",w.address},{"bytes",w.bytes}});
        std::ofstream(argv[3])<<output;return 0;
    }
    const auto seed=Json::parse(Generate("activation-a"));
    const auto other=Json::parse(Generate("activation-b"));
    Json layout={{"schema",1},{"symbols",Json::object()}};
    unsigned address=0x680000;
    for(const auto& [name,value]:seed.at("runtime_fields_hex").items()) {
        const auto size=(name=="rItemOverrides" ? 8192 : value.get<std::string>().size()/2);
        layout["symbols"][name]={address,size};address+=(size+15)&~15u;
    }
    for(const auto* name:{"ptrCustomMessageEntries","numCustomMessageEntries"}) {
        layout["symbols"][name]={address,4};address+=4;
    }
    address+=1; // The real message arena is not word aligned.
    layout["symbols"]["rCustomMessages"]={address,0x7ffff8-address};
    auto plan=PlanSeedActivation(seed,layout); Memory memory;
    ActivateSeed(memory,plan); const auto a=memory.bytes;
    ActivateSeed(memory,PlanSeedActivation(other,layout));Check(a!=memory.bytes);
    ActivateSeed(memory,plan);Check(a==memory.bytes); // Clears data left by larger seeds.
    Memory missing;missing.mapped=false;
    Reject([&]{ActivateSeed(missing,plan);});Check(missing.writes==0);
    auto bad=seed;bad["native_patches"]=Json::array({{{"address",0x100000},{"data_hex","00000000"}}});
    Reject([&]{PlanSeedActivation(bad,layout);});
    bad=seed;bad["native_patches"]=Json::array({{{"address",0x52236c},{"data_hex",std::string(44,'0')}},{{"address",0x52236c},{"data_hex",std::string(44,'0')}}});
    Reject([&]{PlanSeedActivation(bad,layout);});
    bad=seed;bad["runtime_fields_hex"]["gSettingsContext"]="zz";
    Reject([&]{PlanSeedActivation(bad,layout);});
    bad=seed;bad["message_entries_hex"]=std::string(192,'f');
    Reject([&]{PlanSeedActivation(bad,layout);});
    bad=seed;bad["upstream_revision"]="different";
    Reject([&]{PlanSeedActivation(bad,layout);});
    auto overlap=layout;overlap["symbols"]["rCustomMessages"]={0x680000,0x10000};
    Reject([&]{PlanSeedActivation(seed,overlap);});
    std::cerr<<"Seed switching, message bounds, ABI rejection, and preflight checks passed.\n";
}
