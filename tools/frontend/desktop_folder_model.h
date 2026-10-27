// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <cstdlib>
#include <filesystem>
#include <string>
#include <vector>

namespace RetunedFrontend::DesktopFolders {
namespace fs = std::filesystem;
inline std::string Text(const fs::path& path) {
    const auto text = path.u8string();
    return {text.begin(), text.end()};
}
inline fs::path Path(const std::string& text) {
    return fs::path(std::u8string(text.begin(), text.end()));
}
inline bool IsDirectory(const fs::path& path) {
    std::error_code error;
    return fs::is_directory(path, error) && !error;
}
inline fs::path Home() {
#if defined(_WIN32)
    const char* home = std::getenv("USERPROFILE");
#else
    const char* home = std::getenv("HOME");
#endif
    if (home && IsDirectory(Path(home))) return Path(home);
    std::error_code error;
    auto current = fs::current_path(error);
    return error ? fs::path{} : current;
}
struct Listing {
    std::vector<fs::path> directories;
    std::string error;
    bool truncated = false;
};
inline Listing List(const fs::path& path) {
    Listing result;
    std::error_code error;
    fs::directory_iterator entry(path, error), end;
    if (error) {
        result.error = "Unable to open this folder: " + error.message();
        return result;
    }
    std::size_t visited = 0;
    for (; entry != end; entry.increment(error)) {
        if (error) break;
        if (++visited > 4096) { result.truncated = true; break; }
        if (IsDirectory(entry->path())) result.directories.push_back(entry->path());
    }
    if (error) result.error = "Unable to finish reading this folder: " + error.message();
    std::sort(result.directories.begin(), result.directories.end());
    return result;
}
inline std::vector<fs::path> Roots() {
    std::vector<fs::path> result;
#if defined(_WIN32)
    for (char drive = 'A'; drive <= 'Z'; ++drive) {
        auto path = Path(std::string(1, drive) + ":\\");
        if (IsDirectory(path)) result.push_back(path);
    }
#elif defined(__APPLE__)
    result = {"/", "/Volumes"};
#else
    result = {"/", "/run/media", "/media", "/mnt"};
#endif
    return result;
}
struct Browser {
    fs::path directory;
    Listing listing;
    void Open(const fs::path& path) {
        directory = path;
        listing = List(directory);
    }
    void Begin(const std::string& current) {
        const auto path = Path(current);
        Open(!current.empty() && IsDirectory(path) ? path : Home());
    }
    bool CanSelect() const { return listing.error.empty() && IsDirectory(directory); }
};
}
