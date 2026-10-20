#include "../tools/frontend/texture_memory.h"
#include <map>
#include <vector>
#include <cassert>
#include <memory>
struct Entry { uint64_t bytes, last; bool pinned; };
int main() {
    using namespace RetunedFrontend;
    auto low=SelectMobileTextureBudgets(2*GiB,0);
    assert(low.Decoded==96*MiB && low.Uploaded==128*MiB);
    assert(TextureDecodeLimit(low.Decoded,false)==32*MiB);
    assert(TextureDecodeLimit(low.Decoded,true)==96*MiB);
    auto budget=SelectMobileTextureBudgets(3*GiB,0);
    assert(budget.Decoded==96*MiB && budget.Uploaded==192*MiB);
    budget=SelectMobileTextureBudgets(4*GiB,0);
    assert(budget.Decoded==128*MiB && budget.Uploaded==256*MiB);
    budget=SelectMobileTextureBudgets(8*GiB,0);
    assert(budget.Decoded==192*MiB && budget.Uploaded==384*MiB);
    budget=SelectMobileTextureBudgets(16*GiB,0);
    assert(budget.Decoded==256*MiB && budget.Uploaded==512*MiB);
    budget=SelectMobileTextureBudgets(12*GiB,2*GiB);
    assert(budget.Decoded==128*MiB && budget.Uploaded==256*MiB);
    budget=SelectMobileTextureBudgets(0,0);
    assert(budget.Decoded==128*MiB && budget.Uploaded==256*MiB);
    std::map<int, Entry> cache{{1,{40,1,false}}, {2,{40,3,true}}, {3,{40,2,false}}};
    std::vector<int> retired;
    auto cost=[](const auto& e){return e.second.bytes;};
    auto age=[](const auto& e){return e.second.last;};
    auto eligible=[](const auto& e){return !e.second.pinned;};
    auto retire=[&](const auto& e){retired.push_back(e.first);};
    assert(TrimTextureCache(cache,80,cost,age,eligible,retire)==80);
    assert((retired==std::vector<int>{1}) && cache.contains(2));
    assert(TrimTextureCache(cache,0,cost,age,eligible,retire)==40);
    assert((retired==std::vector<int>{1,3}) && cache.contains(2));
    cache.at(2).pinned=false;
    assert(TrimTextureCache(cache,0,cost,age,eligible,retire)==0 && cache.empty());
    assert(FitsTextureBudget(80,20,100));
    assert(!FitsTextureBudget(80,21,100));
    assert(!FitsTextureBudget(UINT64_MAX,1,100));
    assert(!FitsTextureBudget(0,101,100));
    assert(TrimTextureCache(cache,100,cost,age,eligible,retire)==0);
    struct Texture { uint32_t Width, Height; bool CustomReplacementApplied; uint64_t CustomReplacementHash=0; };
    struct Frame { std::vector<Texture> RetiredTextures; };
    std::map<int,Texture> images{{1,{4,4,true}}, {2,{8,8,false}}};
    std::vector<Frame> frames{{{{4,4,true}}}};
    assert(UploadedTextureBytes(images,frames)==128);
    assert(!FitsTextureBudget(UploadedTextureBytes(images,frames),64,128));
    frames.clear();
    assert(FitsTextureBudget(UploadedTextureBytes(images,frames),64,128));
    // Eviction releases only cache ownership; an active reader stays valid.
    auto reader=std::make_shared<int>(42);
    std::map<int,std::shared_ptr<int>> decoded{{1,reader}};
    TrimTextureCache(decoded,0,[](const auto&){return 4ULL;},
        [](const auto&){return 0ULL;},[](const auto&){return true;},[](const auto&){});
    assert(decoded.empty() && *reader==42);
    struct Alias { uint64_t Native; };
    TextureBudgetConfiguration().Decoded.store(128*MiB);
    TextureBudgetConfiguration().Uploaded.store(256*MiB);
    PublishInterfaceTextureHashes(std::vector<Alias>{{123}});
    assert(IsInterfaceTexture(123) && !IsInterfaceTexture(456));
    // Scene uploads leave room for the 4K interface atlas; it still obeys the total cap.
    images={{1,{8192,6144,true,456}}}; // 192 MiB of scene replacements.
    frames.clear();
    assert(!FitsReplacementBudget(images,frames,4,456));
    assert(FitsReplacementBudget(images,frames,64ULL*1024*1024,123));
    images.emplace(2,Texture{4096,4096,true,123});
    assert(!FitsReplacementBudget(images,frames,4,123));
}
