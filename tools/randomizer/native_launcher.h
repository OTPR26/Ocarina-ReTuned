#pragma once
#include "generator.h"
#include "menu_binding.h"
#include <random>
#if defined(__ANDROID__)
#include "android_documents.h"
#endif

namespace RetunedRandomizer {
// Platforms supply only their safe guest-restart handoff. Generation, artifact
// validation, slot selection, and save isolation are shared.
class NativeLauncher {
public:
    NativeLauncher(const std::filesystem::path& appData,
                   const std::filesystem::path& artifacts, PreparedRun installed,
                   RetunedFrontend::RandomizerMenuState& menu,
                   std::function<bool()> atStartup,
                   std::function<bool(const LaunchRequest&)> launch,
                   bool development=false,
                   std::vector<std::filesystem::path> retainedModules={},
                   std::filesystem::path runtimeStore={},
                   RunLauncher::Prepare prepare={},
                   bool restoreInstalled=false)
      : launcher_(appData,
          [](const std::string& requested,const auto& progress) {
              auto seed=requested;
              if(seed.empty()) {
                  std::random_device random;
                  seed=std::to_string(random())+"-"+std::to_string(random());
              }
              return Generate(seed,[&](unsigned attempt){
                  progress("Generating seed (attempt "+std::to_string(attempt)+")…");
              });
          },
          prepare ? std::move(prepare) : RunLauncher::Prepare([installed,artifacts,development](const auto& seed,const auto& progress) {
              progress("Preparing new run…");
              return BindSeedToRuntime(installed,seed,artifacts,development);
          }),
          [appData,artifacts,installed,retainedModules=std::move(retainedModules),runtimeStore,development,restoreInstalled](unsigned slot) {
              const auto run=RunCatalog(appData).Read(slot);
              auto modules=retainedModules;
              if(!installed.module.empty())modules.insert(modules.begin(),installed.module);
              try {
                  return ResolveRunRuntime(artifacts/run.runtimeHash/run.seedHash/"process-manifest.json",
                                           modules,run.runtimeHash,run.seedHash,development);
              } catch(const std::exception&) {
                  if(restoreInstalled && !installed.module.empty())
                      return RestoreRunRuntime(run,{installed},artifacts,development);
                  if(runtimeStore.empty())throw;
                  return RestoreRunRuntime(run,RetainedRuntimeInventory(runtimeStore),artifacts,development);
              }
          },development),
        binding_(launcher_,menu,atStartup,std::move(launch))
#if defined(__ANDROID__)
        ,documents_(menu,std::move(atStartup))
#endif
        {}
    void Poll() {
        binding_.Poll();
#if defined(__ANDROID__)
        documents_.Poll();
#endif
    }
private:
    RunLauncher launcher_;
    MenuBinding binding_;
#if defined(__ANDROID__)
    AndroidDocuments documents_;
#endif
};
}
