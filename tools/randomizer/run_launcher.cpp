#include "run_launcher.h"
#include "seed_activation.h"
#include "run_transfer.h"
#include <triaevum/sha256.h>
#include <nlohmann/json.hpp>
#include <fstream>
#include <chrono>

namespace RetunedRandomizer {
namespace {
std::string Read(const std::filesystem::path& path, std::uintmax_t limit) {
    if (std::filesystem::is_symlink(path) || !std::filesystem::is_regular_file(path) ||
        std::filesystem::file_size(path) > limit)
        throw std::runtime_error("Prepared randomizer file is missing or invalid");
    std::ifstream in(path, std::ios::binary);
    in.exceptions(std::ios::badbit | std::ios::failbit);
    std::string bytes(std::filesystem::file_size(path), '\0');
    in.read(bytes.data(), bytes.size());
    return bytes;
}
std::string Hash(const std::string& bytes) {
    static constexpr char digits[] = "0123456789abcdef";
    std::string result;
    for (auto b : triaevum::module::detail::Sha256(std::span(
        reinterpret_cast<const std::uint8_t*>(bytes.data()), bytes.size()))) {
        result += digits[b >> 4]; result += digits[b & 15];
    }
    return result;
}
struct Identity { std::string seed, runtime; std::size_t extended; bool validatedSeed = false; };
Identity Validate(const PreparedRun& prepared, bool development) {
    const auto manifest = nlohmann::json::parse(Read(prepared.manifest, 8 * 1024 * 1024));
    const auto& proof = manifest.at("randomizer_proof");
    if (proof.at("schema") != 1 ||
        (!development && !proof.at("activation_allowed").get<bool>()))
        throw std::runtime_error("Randomizer runtime is not approved for this launcher");
    Identity id{proof.at("seed_sha256"), manifest.at("source").at("code_bin_sha256"),
                proof.at("extended_save_size")};
    if (id.seed.size() != 64 || id.runtime.size() != 64 || id.extended != 1244)
        throw std::runtime_error("Unsupported randomizer runtime identity or save ABI");
    auto code = std::filesystem::path(manifest.at("source").at("code_bin_path").get<std::string>());
    if (code.is_relative()) code = prepared.manifest.parent_path() / code;
    if (Hash(Read(code, 32 * 1024 * 1024)) != id.runtime)
        throw std::runtime_error("Prepared randomizer image has changed");
    // The preparation adapter must provide the module from this image's build.
    // Check its recorded digest as well as the image, rather than trusting a path.
    const auto framework = prepared.module.parent_path();
    const auto bindingPath = framework.extension() == ".framework"
        ? framework.parent_path().parent_path() / "PrivateGame/randomizer-framework.json"
        : std::filesystem::path(prepared.module.string() + ".randomizer.json");
    const auto binding = nlohmann::json::parse(Read(bindingPath, 16384));
    const bool shared=proof.contains("seed_layout");
    const bool matching=shared
        ? binding.at("format")=="retuned-randomizer-module-v2" &&
          binding.at("seed_layout_sha256")==Hash(proof.at("seed_layout").dump())
        : binding.at("format")=="retuned-randomizer-module-v1" && binding.at("seed_sha256")==id.seed;
    if (shared) {
        if(proof.at("seed_file")!="seed.json")throw std::runtime_error("Invalid runtime seed filename");
        const auto bytes=Read(prepared.manifest.parent_path()/"seed.json",8*1024*1024);
        if(Hash(bytes)!=id.seed)throw std::runtime_error("Prepared runtime seed has changed");
        if(!development) {
            PlanSeedActivation(nlohmann::json::parse(bytes), proof.at("seed_layout"));
            id.validatedSeed = true;
        }
    }
    if (!matching ||
        binding.at("code_sha256") != id.runtime ||
        binding.at("module_sha256") != Hash(Read(prepared.module, 512 * 1024 * 1024)))
        throw std::runtime_error("Prepared module does not match this randomizer run");
    return id;
}
}
PreparedRun ResolveRunRuntime(const std::filesystem::path& manifest,
                             const std::vector<std::filesystem::path>& modules,
                             const std::string& runtimeHash,const std::string& seedHash,
                             bool development) {
    for(const auto& module:modules) {
        PreparedRun candidate{manifest,module};
        try {
            const auto identity=Validate(candidate,development);
            if(identity.runtime==runtimeHash && identity.seed==seedHash)return candidate;
        } catch(const std::exception&) {
            // A missing or incompatible installed module must not mask a valid
            // retained module. No candidate is loaded while checking it.
        }
    }
    throw std::runtime_error("This run needs its matching randomizer runtime. Its saves have been preserved.");
}
PreparedRun BindSeedToRuntime(const PreparedRun& installed, const std::string& seed,
                             const std::filesystem::path& artifacts, bool development) {
    const auto identity=Validate(installed,development);
    auto manifest=nlohmann::json::parse(Read(installed.manifest,8*1024*1024));
    auto& proof=manifest.at("randomizer_proof");
    if(!proof.contains("seed_layout"))
        throw std::runtime_error("Installed randomizer needs a seed-independent runtime update");
    if(seed.size()>8*1024*1024)throw std::runtime_error("Randomizer seed is too large");
    PlanSeedActivation(nlohmann::json::parse(seed),proof.at("seed_layout"));
    const auto hash=Hash(seed);
    const auto destination=artifacts/identity.runtime/hash;
    PreparedRun result{destination/"process-manifest.json",std::filesystem::absolute(installed.module)};
    if(std::filesystem::exists(destination)) {
        const auto cached=Validate(result,development);
        if(cached.seed!=hash || cached.runtime!=identity.runtime)
            throw std::runtime_error("Cached randomizer run identity changed");
        return result;
    }
    // Relocate every source dependency, including the executable header.
    for(auto& [key,value]:manifest["source"].items()) {
        if(!key.ends_with("_path"))continue;
        auto path=std::filesystem::path(value.get<std::string>());
        if(path.is_relative())path=installed.manifest.parent_path()/path;
        value=std::filesystem::absolute(path).lexically_normal().string();
    }
    proof["seed_sha256"]=hash;proof["seed_file"]="seed.json";
    std::filesystem::create_directories(destination.parent_path());
    const auto staging=destination.string()+".pending";
    if(!std::filesystem::create_directory(staging))
        throw std::runtime_error("Randomizer run preparation is already pending");
    try {
        const auto write=[](const auto& path,const std::string& bytes) {
            std::ofstream out(path,std::ios::binary);
            out.exceptions(std::ios::badbit|std::ios::failbit);
            out.write(bytes.data(),bytes.size());out.close();
        };
        write(std::filesystem::path(staging)/"seed.json",seed);
        write(std::filesystem::path(staging)/"process-manifest.json",manifest.dump(2));
        Validate({std::filesystem::path(staging)/"process-manifest.json",result.module},development);
        std::filesystem::rename(staging,destination);
    } catch(...) {std::filesystem::remove_all(staging);throw;}
    return result;
}
std::vector<PreparedRun> RetainedRuntimeInventory(const std::filesystem::path& store) {
    std::vector<PreparedRun> result;
    const auto root=store/"runtimes";
    if(!std::filesystem::exists(root))return result;
    if(std::filesystem::is_symlink(root))throw std::runtime_error("Invalid runtime inventory directory");
    unsigned count=0;
    for(const auto& entry:std::filesystem::directory_iterator(root)) {
        if(++count>1024)throw std::runtime_error("Runtime inventory is too large");
        const auto name=entry.path().filename().string();
        if(name.size()!=64 || name.find_first_not_of("0123456789abcdef")!=std::string::npos ||
           entry.is_symlink() || !entry.is_directory())continue;
        for(const char* module:{"title.dylib","title.so","title.dll"}) {
            const auto path=entry.path()/module;
            if(std::filesystem::is_regular_file(path) && !std::filesystem::is_symlink(path))
                result.push_back({entry.path()/"process-manifest.json",path});
        }
    }
    std::sort(result.begin(),result.end(),[](const auto& a,const auto& b){return a.module<b.module;});
    return result;
}
PreparedRun RestoreRunRuntime(const RunSlot& run,const std::vector<PreparedRun>& inventory,
                             const std::filesystem::path& artifacts,bool development) {
    if(run.status!=RunStatus::Ready)throw std::runtime_error("Randomizer run is unavailable");
    const auto seed=Read(run.profile.parent_path()/"seed.json",8*1024*1024);
    if(Hash(seed)!=run.seedHash)throw std::runtime_error("Randomizer run seed changed");
    for(const auto& prepared:inventory) {
        try {
            if(Validate(prepared,development).runtime!=run.runtimeHash)continue;
        } catch(const std::exception&) { continue; }
        // Use a separate binding directory: do not rewrite old manifests that
        // may still belong to a running guest or depend on obsolete build paths.
        return BindSeedToRuntime(prepared,seed,artifacts/"retained",development);
    }
    throw std::runtime_error("The matching retained runtime is missing. Its saves have been preserved.");
}
RunLauncher::RunLauncher(const std::filesystem::path& data, Generate generate,
                         Prepare prepare, Resolve resolve, bool development)
    : appData_(data), catalog_(data), generate_(std::move(generate)), prepare_(std::move(prepare)),
      resolve_(std::move(resolve)), development_(development) {
    if (!generate_ || !prepare_ || !resolve_) throw std::invalid_argument("Missing randomizer launcher service");
}
RunLauncher::~RunLauncher() { Cancel(); if (pending_.valid()) pending_.wait(); }
bool RunLauncher::Busy() const { return pending_.valid(); }
std::string RunLauncher::Status() const { std::lock_guard lock(mutex_); return status_; }
void RunLauncher::Report(const std::string& text) {
    if (cancel_) throw std::runtime_error("Randomizer operation cancelled");
    std::lock_guard lock(mutex_); status_ = text;
}
void RunLauncher::Cancel() { cancel_ = true; }
std::array<RunSlot, 3> RunLauncher::Slots() const { return catalog_.List(); }
bool RunLauncher::Create(unsigned slot, const std::string& seed) { return Begin(slot, seed); }
bool RunLauncher::Continue(unsigned slot) { return Begin(slot, std::nullopt); }
std::string RunLauncher::Export(unsigned slot) const {
    if (Busy()) throw std::runtime_error("Wait for the current randomizer operation");
    return ExportRun(appData_,slot);
}
bool RunLauncher::Import(unsigned slot,const std::string& bundle) {
    if (Busy() || slot>=3 || catalog_.Read(slot).status!=RunStatus::Empty) return false;
    cancel_=false;
    Report("Checking imported run…");
    pending_=std::async(std::launch::async,[this,slot,bundle] {
        const auto incoming=ReadRunBundle(bundle);
        const Progress progress=[this](const auto& text){Report(text);};
        Report("Preparing imported run…");
        const auto prepared=prepare_(incoming.seed,progress);
        const auto identity=Validate(prepared,development_);
        if(identity.runtime!=incoming.runtime || identity.seed!=Hash(incoming.seed))
            throw std::runtime_error("Imported run requires its matching prepared runtime");
        Report("Restoring run…");
        auto run=ImportRun(appData_,slot,bundle,identity.runtime,development_ || identity.validatedSeed);
        return LaunchRequest{prepared,run,slot,0};
    });
    return true;
}
bool RunLauncher::Begin(unsigned slot, std::optional<std::string> seed) {
    if (Busy() || slot >= 3) return false;
    const auto existing = catalog_.Read(slot);
    if (existing.status != (seed ? RunStatus::Empty : RunStatus::Ready)) return false;
    cancel_ = false;
    Report(seed ? "Generating seed…" : "Checking run…");
    pending_ = std::async(std::launch::async, [this, slot, seed] {
        const Progress progress = [this](const auto& text) { Report(text); };
        std::string generated;
        PreparedRun prepared;
        if (seed) {
            generated = generate_(*seed, progress);
            Report("Preparing randomized game…");
            prepared = prepare_(generated, progress);
        } else prepared = resolve_(slot);
        Report("Verifying randomized game…");
        const auto identity = Validate(prepared, development_);
        if (seed && identity.seed != Hash(generated))
            throw std::runtime_error("Preparation returned a different seed");
        Report("Opening run…");
        auto run = seed ? catalog_.Create(slot, generated, identity.runtime, identity.extended, development_ || identity.validatedSeed)
                        : catalog_.Select(slot, identity.runtime);
        if (run.seedHash != identity.seed || run.extendedSize != identity.extended)
            throw std::runtime_error("Prepared game does not match the selected run");
        return LaunchRequest{prepared, run, slot, 0};
    });
    return true;
}
std::optional<LaunchRequest> RunLauncher::Poll() {
    if (!pending_.valid() || pending_.wait_for(std::chrono::seconds(0)) != std::future_status::ready)
        return std::nullopt;
    try {
        auto request = pending_.get();
        if (cancel_) throw std::runtime_error("Randomizer operation cancelled; any created run has been retained");
        Report("Ready");
        return request;
    } catch (const std::exception& error) {
        std::lock_guard lock(mutex_); status_ = error.what();
        return std::nullopt;
    }
}
}
