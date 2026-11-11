#include "macos_profile.h"
#include <cassert>
int main(int argc, char** argv) {
    namespace fs=std::filesystem;
    using Json=nlohmann::json;
    const fs::path root=argv[1], profile=root/"native-launch.json", resources=root/"New/Ocarina ReTuned.app/Contents/Resources";
    fs::create_directories(resources);
    auto old=root/"Old/Ocarina ReTuned.app/Contents/Resources";
    Json original={{"format","oot3d_native_game_launch_profile_v1"},{"arguments",{"--resource-root",old.string(),"--save-data","preserved saves","--config","preserved config"}},{"custom",42}};
    auto write=[&](const Json& data){std::ofstream(profile)<<data.dump();};
    auto read=[&](){std::ifstream f(profile);return Json::parse(f);};
    write(original);
    assert(RetunedSetup::RepairMacResourcePath(profile,resources));
    auto expected=original;expected["arguments"][1]=resources.string();assert(read()==expected);
    assert(!RetunedSetup::RepairMacResourcePath(profile,resources));
    fs::create_directories(old);write(original);
    assert(!RetunedSetup::RepairMacResourcePath(profile,resources));assert(read()==original);
    original["arguments"][1]=(root/"missing-custom-resources").string();write(original);
    assert(!RetunedSetup::RepairMacResourcePath(profile,resources));assert(read()==original);
    std::ofstream(profile)<<"invalid";
    try { RetunedSetup::RepairMacResourcePath(profile,resources);assert(false); } catch(const Json::exception&) {}
    std::ifstream f(profile);std::string text;f>>text;assert(text=="invalid");
}
