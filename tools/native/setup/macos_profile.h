#pragma once
#include <filesystem>
#include <fstream>
#include <nlohmann/json.hpp>
#include <stdexcept>

namespace RetunedSetup {
inline bool RepairMacResourcePath(const std::filesystem::path& profile,
                                  const std::filesystem::path& resources) {
    namespace fs = std::filesystem;
    if (!fs::is_regular_file(profile) || !fs::is_directory(resources)) return false;
    std::ifstream input(profile);
    auto document = nlohmann::json::parse(input);
    if (document.value("format", "") != "oot3d_native_game_launch_profile_v1") return false;
    auto& args = document.at("arguments");
    if (!args.is_array()) return false;
    bool changed = false;
    for (size_t i = 0; i + 1 < args.size(); ++i) {
        if (args[i] != "--resource-root" || !args[i + 1].is_string()) continue;
        const fs::path old(args[i + 1].get<std::string>());
        if (old.filename() != "Resources" || old.parent_path().filename() != "Contents" ||
            old.parent_path().parent_path().filename() != "Ocarina ReTuned.app" || fs::exists(old)) continue;
        args[i + 1] = resources.string();
        changed = true;
    }
    if (!changed) return false;
    auto temporary = profile;
    temporary += ".resource-path-update";
    if (fs::exists(temporary) || fs::is_symlink(temporary))
        throw std::runtime_error("A resource-path update is already pending.");
    try {
        std::ofstream output(temporary);
        output << document.dump(2) << '\n';
        output.close();
        if (!output) throw std::runtime_error("Cannot save updated resource path.");
        fs::permissions(temporary, fs::status(profile).permissions());
        fs::rename(temporary, profile);
    } catch (...) {
        std::error_code error;
        fs::remove(temporary, error);
        throw;
    }
    return true;
}
}
