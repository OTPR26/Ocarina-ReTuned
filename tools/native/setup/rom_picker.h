#pragma once
#include <algorithm>
#include <cctype>
#include <filesystem>
#include <string>
#include <vector>

namespace RetunedRomPicker {
namespace fs = std::filesystem;
inline bool IsRom(const fs::path& path) {
    auto extension = path.extension().string();
    std::transform(extension.begin(), extension.end(), extension.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    std::error_code error;
    return (extension == ".3ds" || extension == ".cci") && fs::is_regular_file(path, error);
}
struct Entry { fs::path path; bool directory; };
struct Listing {
    std::vector<Entry> entries;
    std::string error;
    bool truncated = false;
};
inline Listing List(const fs::path& directory) {
    Listing result;
    std::error_code error;
    fs::directory_iterator it(directory, error), end;
    if (error) { result.error = "Unable to open this folder: " + error.message(); return result; }
    std::size_t visited = 0;
    for (; it != end; it.increment(error)) {
        if (error) break;
        // Bound even folders containing many unsupported files. The location
        // field still accepts an exact path when a listing is truncated.
        if (++visited > 4096) { result.truncated = true; break; }
        std::error_code entryError;
        bool folder = it->is_directory(entryError);
        if (!entryError && (folder || IsRom(it->path())))
            result.entries.push_back({it->path(), folder});
    }
    if (error) result.error = "Unable to finish reading this folder: " + error.message();
    std::sort(result.entries.begin(), result.entries.end(), [](const Entry& a, const Entry& b) {
        if (a.directory != b.directory) return a.directory;
        return a.path.filename() < b.path.filename();
    });
    return result;
}
}
