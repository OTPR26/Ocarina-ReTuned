#pragma once
#include "host_adapter.h"
#include "seed_activation.h"
#include <triaevum/sha256.h>
#include <nlohmann/json.hpp>
#include <cstdio>

namespace RetunedRandomizer {
inline void BindProofProfile(Oot3dNativeGame::NativeA32CtrHostConfig& config,
                             const std::filesystem::path& manifestPath) {
    nlohmann::json manifest;
    std::ifstream input(manifestPath);input>>manifest;
    const auto& proof=manifest.at("randomizer_proof");
    if(proof.at("schema")!=1 || config.Filesystem || config.SaveDataDirectory.empty())
        throw std::runtime_error("Invalid isolated randomizer launch");
    const auto root=config.SaveDataDirectory;
    auto store=std::make_shared<SaveStore>(root,proof.at("seed_sha256").get<std::string>(),
        manifest.at("source").at("code_bin_sha256").get<std::string>(),
        proof.at("extended_save_size").get<std::size_t>(),!std::filesystem::exists(root));
    std::filesystem::create_directory(root/"native");
    config.SaveDataDirectory=std::filesystem::canonical(root/"native");
    struct Binding {Oot3dNativeGame::NativeA32CtrHostConfig callbacks;bool active=false;};
    auto binding=std::make_shared<Binding>();
    const auto address=proof.at("extended_save_address").get<std::uint32_t>();
    const auto size=proof.at("extended_save_size").get<std::size_t>();
    config.RandomizerSvc=[binding,store,address,size](auto svc,auto& state,auto& memory){
        if(!binding->active){BindHostServices(binding->callbacks,memory,store,address,size);binding->active=true;}
        const auto argument=state.r[0];
        const bool handled=binding->callbacks.RandomizerSvc(svc,state,memory);
        if(svc>=0xfff401 && svc<=0xfff404)
            std::fprintf(stderr,"Randomizer service=%06x argument=%u completed\n",svc,argument);
        return handled;
    };
    config.WriteRandomizerSave=[binding](const auto& path,auto offset,auto bytes)->std::optional<bool>{
        if(!binding->active) {
            const auto name=path.filename().string();
            if(name=="save00.bin" || name=="save01.bin" || name=="save02.bin")
                throw std::runtime_error("Randomizer save before initialization");
            return std::nullopt;
        }
        std::optional<bool> handled;
        try {handled=binding->callbacks.WriteRandomizerSave(path,offset,bytes);}
        catch(const std::exception& error) {
            std::fprintf(stderr,"Randomizer save failure file=%s offset=%llu bytes=%zu reason=%s\n",
                path.filename().string().c_str(),static_cast<unsigned long long>(offset),bytes.size(),error.what());
            throw;
        }
        if(handled.has_value())std::fprintf(stderr,"Randomizer native save committed=%d bytes=%zu\n",int(*handled),bytes.size());
        return handled;
    };
}
// Called immediately after mounting a fresh image, before any guest code runs.
inline void ActivateProofSeedIfPresent(Oot3dNativeGame::NativeA32Memory& memory,
                                      const std::filesystem::path& manifestPath) {
    nlohmann::json manifest;
    std::ifstream(manifestPath) >> manifest;
    if (!manifest.contains("randomizer_proof")) return;
    const auto& proof=manifest.at("randomizer_proof");
    if (!proof.contains("seed_layout")) return;
    const auto name=std::filesystem::path(proof.at("seed_file").get<std::string>());
    if (name != "seed.json") throw std::runtime_error("Invalid runtime seed filename");
    const auto path=manifestPath.parent_path()/name;
    if(std::filesystem::is_symlink(path) || std::filesystem::file_size(path)>8*1024*1024)
        throw std::runtime_error("Invalid runtime seed file");
    std::ifstream input(path,std::ios::binary);
    input.exceptions(std::ios::badbit);
    const std::string bytes{std::istreambuf_iterator<char>(input),{}};
    const auto hash=triaevum::module::detail::Sha256(std::span(
        reinterpret_cast<const std::uint8_t*>(bytes.data()),bytes.size()));
    std::string digest;const char* hex="0123456789abcdef";
    for(auto byte:hash){digest+=hex[byte>>4];digest+=hex[byte&15];}
    if(digest!=proof.at("seed_sha256").get<std::string>())throw std::runtime_error("Runtime seed identity mismatch");
    ActivateSeed(memory,PlanSeedActivation(nlohmann::json::parse(bytes),proof.at("seed_layout")));
}
inline void BindProofProfileIfPresent(Oot3dNativeGame::NativeA32CtrHostConfig& config,
                                      const std::filesystem::path& manifestPath) {
    std::ifstream input(manifestPath); nlohmann::json manifest; input >> manifest;
    if (manifest.contains("randomizer_proof")) BindProofProfile(config, manifestPath);
}

}
