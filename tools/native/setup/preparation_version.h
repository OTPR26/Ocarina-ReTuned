// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include <nlohmann/json.hpp>

namespace RetunedSetup {
inline bool PreparedIdentityMatches(const std::filesystem::path& profile,const std::string& identity) {
    if(identity.size()!=64 || !std::all_of(identity.begin(),identity.end(),[](char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');}))return false;
    try {
        std::ifstream input(profile);
        const auto arguments=nlohmann::json::parse(input).at("arguments").get<std::vector<std::string>>();
        auto found=std::find(arguments.begin(),arguments.end(),"--a32-process-manifest");
        if(found==arguments.end()||++found==arguments.end())return false;
        const auto& text=*found;
        const std::filesystem::path manifest(std::u8string(text.begin(),text.end()));
        std::ifstream receipt(manifest.parent_path()/"setup-receipt.json");
        return nlohmann::json::parse(receipt).value("preparation_identity",std::string{})==identity;
    }catch(...){return false;}
}
}
