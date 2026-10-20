#pragma once
#include <cstdint>
#include <vector>
namespace Oot3d::Renderer {
struct TextureHashAlias { uint64_t Native=0,Original=0;bool Modern=false;bool operator==(const TextureHashAlias&)const=default; };
template<class Index>
void ApplyTextureHashAliases(Index& index,const std::vector<TextureHashAlias>& aliases,bool modern) {
    // Resolve against the pack's own entries. Never chain aliases or replace
    // an explicit texture supplied for the modified atlas.
    const auto original=index;
    for(const auto& alias:aliases) {
        if(alias.Modern!=modern || !alias.Native || !alias.Original)continue;
        const auto match=original.find(alias.Original);
        if(match!=original.end())index.try_emplace(alias.Native,match->second);
    }
}
}
