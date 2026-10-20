// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <functional>
#include <string>
#include <vector>
#include <cstdint>
#include <stdexcept>
namespace RetunedFrontend {
// Platform callbacks are installed before the native host starts.
struct TextureFolderAccess {
 std::function<void()> Choose;
 std::function<std::string()> TakeSelection;
 std::function<std::string()> Status;
 std::function<std::vector<uint8_t>(const std::string&)> Read;
};
inline TextureFolderAccess TextureFolders;
inline bool IsTextureDocument(const std::string& path){return path.find("/retuned-texture-links/")!=std::string::npos;}
inline std::vector<uint8_t> ReadTextureDocument(const std::string& path){
 if(!TextureFolders.Read)throw std::runtime_error("Texture folder access is unavailable. Choose the folder again.");
 return TextureFolders.Read(path);
}
}
