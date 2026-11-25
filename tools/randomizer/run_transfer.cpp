#include "run_transfer.h"
#include <triaevum/sha256.h>
#include <nlohmann/json.hpp>
#include <fstream>

namespace RetunedRandomizer {
namespace {
using Json=nlohmann::json;
constexpr std::size_t MaxBundle=10*1024*1024;
void Require(bool ok,const char* reason) {if(!ok)throw std::runtime_error(reason);}
std::string Hash(const std::string& bytes) {
    const char* hex="0123456789abcdef";std::string out;
    for(auto b:triaevum::module::detail::Sha256(std::span(
        reinterpret_cast<const std::uint8_t*>(bytes.data()),bytes.size()))) {
        out+=hex[b>>4];out+=hex[b&15];
    }
    return out;
}
std::string Read(const std::filesystem::path& path,std::size_t limit) {
    Require(!std::filesystem::is_symlink(path) && std::filesystem::is_regular_file(path) &&
        std::filesystem::file_size(path)<=limit,"Invalid randomizer transfer source");
    std::ifstream input(path,std::ios::binary);
    input.exceptions(std::ios::badbit | std::ios::failbit);
    std::string bytes(std::filesystem::file_size(path), '\0');
    Require(bytes.size()<=limit,"Randomizer transfer source grew during export");
    input.read(bytes.data(),bytes.size());
    Require(input.peek()==std::char_traits<char>::eof(),"Randomizer transfer source grew during export");
    return bytes;
}
std::string Hex(const Bytes& bytes) {
    const char* hex="0123456789abcdef";std::string out;
    for(auto b:bytes){out+=hex[b>>4];out+=hex[b&15];}return out;
}
Bytes Decode(const Json& field,std::size_t size) {
    const auto& text=field.get_ref<const std::string&>();
    Require(text.size()==size*2,"Invalid transferred save size");
    auto digit=[](char c)->unsigned {
        if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;
        throw std::runtime_error("Invalid transferred save encoding");
    };
    Bytes out;out.reserve(size);
    for(std::size_t i=0;i<text.size();i+=2)out.push_back(digit(text[i])*16+digit(text[i+1]));
    return out;
}
}
std::string ExportRun(const std::filesystem::path& data,unsigned slot) {
    const auto run=RunCatalog(data).Read(slot);
    Require(run.status==RunStatus::Ready,"Randomizer run is not ready to export");
    const auto seed=Read(run.profile.parent_path()/"seed.json",8*1024*1024);
    Require(Hash(seed)==run.seedHash,"Randomizer seed changed during export");
    SaveStore store(run.profile,run.seedHash,run.runtimeHash,run.extendedSize,false);
    Require(!std::filesystem::is_symlink(run.profile/"native"),"Invalid randomizer save directory");
    Json saves=Json::array();std::vector<std::pair<std::filesystem::path,std::string>> snapshot;
    for(unsigned index=0;index<3;++index) {
        const auto path=run.profile/"native"/("save0"+std::to_string(index)+".bin");
        if(!std::filesystem::exists(path) && !std::filesystem::is_symlink(path))continue;
        const auto bytes=Read(path,0x14dc);Bytes native(bytes.begin(),bytes.end());
        const auto extended=store.Load(index,native);
        saves.push_back({{"slot",index},{"native_hex",Hex(native)},{"extended_hex",Hex(extended)}});
        snapshot.emplace_back(path,bytes);
    }
    Require(!saves.empty(),"Create an in-game save before exporting this run");
    std::string system;
    const auto systemPath=run.profile/"native/system.dat";
    if(std::filesystem::exists(systemPath) || std::filesystem::is_symlink(systemPath)) {
        system=Read(systemPath,34);Require(system.size()==34,"Invalid randomizer system save");
        snapshot.emplace_back(systemPath,system);
    }
    for(const auto& [path,bytes]:snapshot)
        Require(Read(path,bytes.size())==bytes,"Run changed during export; stop gameplay and try again");
    Json payload={{"seed_json",seed},{"seed_sha256",run.seedHash},{"runtime_sha256",run.runtimeHash},
        {"extended_save_size",run.extendedSize},{"saves",saves},{"system_hex",Hex(Bytes(system.begin(),system.end()))}};
    const auto bundle=Json{{"format","retuned-run-bundle-v1"},{"payload",payload},{"sha256",Hash(payload.dump())}}.dump();
    Require(bundle.size()<=MaxBundle,"Randomizer run bundle is too large");return bundle;
}
RunBundle ReadRunBundle(const std::string& bundle) {
    Require(bundle.size()<=MaxBundle,"Randomizer run bundle is too large");
    const auto parsed=Json::parse(bundle);const auto& payload=parsed.at("payload");
    Require(parsed.size()==3 && parsed.at("format")=="retuned-run-bundle-v1" &&
        parsed.at("sha256")==Hash(payload.dump()),"Invalid randomizer run bundle checksum");
    Require(payload.size()==6 && payload.at("runtime_sha256").is_string() &&
        payload.at("extended_save_size")==1244,"This run requires its matching prepared randomizer runtime");
    const auto seed=payload.at("seed_json").get<std::string>();
    Require(seed.size()<=8*1024*1024 && payload.at("seed_sha256")==Hash(seed),"Transferred seed identity mismatch");
    const auto& entries=payload.at("saves");
    Require(entries.is_array() && !entries.empty() && entries.size()<=3,"Invalid run save count");
    std::vector<RunSave> saves;
    for(const auto& entry:entries) {
        Require(entry.size()==3,"Unexpected transferred save fields");
        Require(entry.at("slot").is_number_unsigned() && entry.at("slot") < 3,
                "Invalid transferred save slot");
        saves.push_back({entry.at("slot").get<unsigned>(),Decode(entry.at("native_hex"),0x14dc),
                         Decode(entry.at("extended_hex"),1244)});
    }
    Bytes system;
    if(payload.at("system_hex")!="")system=Decode(payload.at("system_hex"),34);
    const auto runtime=payload.at("runtime_sha256").get<std::string>();
    Require(runtime.size()==64 && runtime.find_first_not_of("0123456789abcdef")==std::string::npos,
            "Invalid transferred runtime identity");
    unsigned seen=0;
    for(const auto& save:saves) {
        Require(!(seen & (1U<<save.slot)),"Duplicate transferred save slot");
        seen |= 1U<<save.slot;
    }
    return {seed,runtime,std::move(saves),std::move(system)};
}
RunSlot ImportRun(const std::filesystem::path& data,unsigned slot,const std::string& bundle,
                  const std::string& runtime,bool development) {
    const auto parsed=ReadRunBundle(bundle);
    Require(parsed.runtime==runtime,"This run requires its matching prepared randomizer runtime");
    // Restore reserves an empty slot and publishes run.json only after every
    // paired save is committed. It never replaces another run or normal save.
    return RunCatalog(data).Restore(slot,parsed.seed,runtime,1244,parsed.saves,parsed.system,development);
}
}
