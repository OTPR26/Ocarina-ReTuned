// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <deko3d.h>
#include <map>
#include <memory>
#include <string>
#include <vector>
#include <set>
namespace RetunedDeko {
struct Module {
    DkShader shader{};
    std::map<unsigned,unsigned> uniforms, textures, images;
    std::set<unsigned> integerTextures;
};
struct CompilerWorker;
class Shaders {
    std::unique_ptr<CompilerWorker> compiler;
    DkDevice device{};
    DkMemBlock code{};
    unsigned cursor=0;
    std::map<std::pair<int,std::string>,Module> modules;
public:
    explicit Shaders(DkDevice);
    ~Shaders();
    Module& Get(DkStage stage, std::string source);
};
}
