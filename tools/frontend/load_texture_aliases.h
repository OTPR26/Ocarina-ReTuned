#pragma once
#include "oot3d/renderer/azahar_texture_pack.h"
#include <nlohmann/json.hpp>
#include <fstream>
#include <filesystem>
#include <stdexcept>
namespace RetunedFrontend {
inline void LoadTextureAliases(const std::filesystem::path& path) {
    std::ifstream stream(path);nlohmann::json manifest;stream>>manifest;
    std::vector<Oot3d::Renderer::TextureHashAlias> aliases;
    if(manifest.contains("texture_hash_aliases")) {
        const auto& entries=manifest.at("texture_hash_aliases");
        if(!entries.is_array() || entries.size()>256)throw std::runtime_error("Invalid texture compatibility manifest");
        for(const auto& entry:entries)aliases.push_back({entry.at("native").get<uint64_t>(),entry.at("original").get<uint64_t>(),entry.at("modern").get<bool>()});
    }
    Oot3d::Renderer::AzaharTexturePackRuntime::Instance().SetHashAliases(std::move(aliases));
}
}
