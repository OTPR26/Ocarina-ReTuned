#pragma once
#include "run_launcher.h"
#include <algorithm>

namespace RetunedRandomizer {
inline std::vector<std::string> LaunchArguments(const std::filesystem::path& data,
        std::vector<std::string> normal, const LaunchRequest& request) {
    const auto run=RunCatalog(data).Select(request.menuSlot,request.run.runtimeHash);
    if(run.seedHash!=request.run.seedHash ||
       std::filesystem::canonical(run.profile)!=std::filesystem::canonical(request.run.profile))
        throw std::runtime_error("Randomizer launch does not match its save slot");
    const auto set=[&](const std::string& flag,const std::filesystem::path& value) {
        auto found=std::find(normal.begin(),normal.end(),flag);
        if(found==normal.end() || found+1==normal.end() ||
           std::find(found+1,normal.end(),flag)!=normal.end())
            throw std::runtime_error("Invalid normal launch arguments");
        const auto text=value.u8string();
        *(found+1)=std::string(text.begin(),text.end());
    };
    set("--a32-process-manifest",request.prepared.manifest);
    set("--title-plugin",request.prepared.module);
    set("--save-data",run.profile);
    return normal;
}
}
