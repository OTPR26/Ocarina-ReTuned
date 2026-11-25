#include "run_transfer.h"
#include "generator.h"
#include "transfer_files.h"
#include <nlohmann/json.hpp>
#include <fstream>
#include <chrono>
#include <iostream>
using namespace RetunedRandomizer;
namespace fs=std::filesystem;
void Check(bool ok){if(!ok)throw std::runtime_error("Run transfer check failed");}
template<class F>void Reject(F f){bool failed=false;try{f();}catch(const std::exception&){failed=true;}Check(failed);}
int main(int argc,char** argv) {
    if(argc==4 && std::string(argv[1])=="--export") {
        std::ofstream(argv[3],std::ios::binary)<<ExportRun(argv[2],0);return 0;
    }
    if(argc==4 && std::string(argv[1])=="--roundtrip") {
        const auto bundle=ExportRun(argv[2],0);
        const auto runtime=RunCatalog(argv[2]).Read(0).runtimeHash;
        if(!fs::create_directory(argv[3]))throw std::runtime_error("Test destination already exists");
        try {
            ImportRun(argv[3],0,bundle,runtime,true);
            Check(ExportRun(argv[3],0)==bundle);
            fs::remove_all(argv[3]);
        }catch(...){fs::remove_all(argv[3]);throw;}
        std::cerr<<"Existing run roundtrip passed; temporary import removed.\n";
        return 0;
    }
    const auto root=fs::temp_directory_path()/("retuned-transfer-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    fs::create_directory(root);
    try {
        auto source=root/"source",target=root/"target";fs::create_directory(source);fs::create_directory(target);
        std::ofstream(target/"save00.bin")<<"ordinary";
        const std::string runtime(64,'a');
        auto run=RunCatalog(source).Create(0,Generate("transfer-test"),runtime,1244,true);
        Reject([&]{ExportRun(source,0);});
        SaveStore store(run.profile,run.seedHash,runtime,1244,false);
        Bytes native(0x14dc,3),extended(1244,4);store.Commit(0,native,extended);
        std::ofstream(run.profile/"native/system.dat",std::ios::binary)<<std::string(34,'s');
        auto bundle=ExportRun(source,0);
        const auto document=root/"roundtrip.retuned-run";
        WriteRunDocument(document,bundle);
        Check(ReadRunDocument(document)==bundle);
        Reject([&]{WriteRunDocument(document,"replacement");});
        Check(ReadRunDocument(document)==bundle);
        Check(bundle.find(source.string())==std::string::npos);
        Reject([&]{ImportRun(target,0,bundle,std::string(64,'b'),true);});
        Reject([&]{ImportRun(target,0,bundle,runtime,false);});
        Check(RunCatalog(target).Read(0).status==RunStatus::Empty);
        auto corrupted=nlohmann::json::parse(bundle);corrupted["payload"]["saves"][0]["native_hex"]="00";
        Reject([&]{ImportRun(target,0,corrupted.dump(),runtime,true);});
        Check(RunCatalog(target).Read(0).status==RunStatus::Empty);
        auto imported=ImportRun(target,0,bundle,runtime,true);
        Check(imported.seedHash==run.seedHash);
        Check(SaveStore(imported.profile,imported.seedHash,runtime,1244,false).Load(0,native)==extended);
        Check(ExportRun(target,0)==bundle);
        Reject([&]{ImportRun(target,0,bundle,runtime,true);});
        auto second=ImportRun(target,1,bundle,runtime,true);
        Check(second.profile!=imported.profile);
        std::string ordinary;std::getline(std::ifstream(target/"save00.bin"),ordinary);Check(ordinary=="ordinary");
        // Corrupt/missing sidecars must never export a native-only run.
        for(const auto& entry:fs::directory_iterator(run.profile))
            if(entry.path().extension()==".state")fs::remove(entry.path());
        Reject([&]{ExportRun(source,0);});
        Check(ExportRun(target,0)==bundle);
        fs::remove_all(root);
        std::cerr<<"Run transfer roundtrip, integrity, runtime mismatch, and save preservation passed.\n";
    }catch(...){fs::remove_all(root);throw;}
}
