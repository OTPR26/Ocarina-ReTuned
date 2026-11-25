#!/usr/bin/env python3
"""Keep Android's activity and renderer while replacing an isolated guest session."""
from pathlib import Path
from apply_host_services import BASE


def patch(path, old, new):
    text=path.read_text()
    if new in text:return
    if text.count(old)!=1:raise ValueError(f'Unexpected session integration anchor: {path.name}: {old[:60]}')
    path.write_text(text.replace(old,new,1))


def install(engine):
    runtime=engine/BASE
    main=runtime/'oot3d_native_game.cpp'
    patch(main,'#include "android_host.h"','#include "android_host.h"\n#include "android_launcher.h"')
    patch(main,'int main(int argc, char** argv) {','int RetunedAndroidGuestMain(int argc, char** argv) {')
    patch(main,'        InitializeAndroidGameHost();','        static const bool initialized=[] {InitializeAndroidGameHost();return true;}();\n        (void)initialized;')
    patch(main,'        DestroyContextForDemo();\n#if defined(__SWITCH__)',
          '        if(!RetunedRandomizer::AndroidSessions.Pending()) DestroyContextForDemo();\n#if defined(__SWITCH__)')
    text=main.read_text()
    marker='// Android keeps SDL and its Activity alive across guest sessions.'
    if marker not in text:
        text+='''
// Android keeps SDL and its Activity alive across guest sessions.
int main(int argc,char** argv) {
    std::vector<std::string> values;
    std::vector<char*> pointers;
    for(;;) {
        const int result=RetunedAndroidGuestMain(argc,argv);
        auto next=RetunedRandomizer::AndroidSessions.Take();
        if(result!=0 || !next)return result;
        try {
            // No guest or renderer worker still references the old module here.
            RetunedRandomizer::ResetAndroidLauncher();
            Oot3dNativeGame::ResetTitlePluginForSession();
            for(const char* name:{"RETUNED_RANDOMIZER_ACTIVE_SLOT","RETUNED_RANDOMIZER_NEW_GAME",
                                 "RETUNED_RANDOMIZER_CONTINUE","RETUNED_RANDOMIZER_START_NORMAL"})unsetenv(name);
            if(next->randomizerSlot>=0) {
                SDL_setenv("RETUNED_RANDOMIZER_ACTIVE_SLOT",std::to_string(next->randomizerSlot).c_str(),1);
                SDL_setenv(next->newGame?"RETUNED_RANDOMIZER_NEW_GAME":"RETUNED_RANDOMIZER_CONTINUE","1",1);
            } else SDL_setenv("RETUNED_RANDOMIZER_START_NORMAL","1",1);
            RetunedFrontend::StartupVisible=false;
            RetunedFrontend::SetupVisible=false;
            values=std::move(next->arguments);
            values.insert(values.begin(),"Ocarina ReTuned");
            pointers.clear();for(auto& value:values)pointers.push_back(value.data());
            argc=static_cast<int>(pointers.size());argv=pointers.data();
            SDL_Log("Randomizer: replacing guest in the existing Android window");
        } catch(const std::exception& error) {
            RetunedStartupException(error.what());DestroyContextForDemo();return 1;
        }
    }
}
'''
        main.write_text(text)
    window=runtime/'oot3d_native_a32_window.cpp'
    patch(window,'#include "oot3d_native_a32_window.h"','#include "oot3d_native_a32_window.h"\n#include "android_session.h"')
    patch(window,'    if (!RunFrame()) break;','    if (RetunedRandomizer::AndroidSessions.Pending() || !RunFrame()) break;')
    setup=runtime/'oot3d_native_a32_window_setup.cpp'
    patch(setup,'  InitContextForDemo(hostArgs);','''  const bool retainedContext=Ship::Context::GetRawInstance()!=nullptr;
  if(!retainedContext) InitContextForDemo(hostArgs);''')
    patch(setup,'  auto &api = *apiPointer;','''  auto &api = *apiPointer;
  if(retainedContext) {
    api.WaitForIdle();
    std::string error;
    if(!api.ResetPicaState(&error))throw std::runtime_error("Could not reset renderer for the next game: "+error);
  }''')
    patch(setup,'      dynamic_cast<Fast::Oot3d::TitleRenderBackend *>(&api);','''      dynamic_cast<Fast::Oot3d::TitleRenderBackend *>(&api);
  if(retainedContext && titleRenderBackend) {
    std::string error;
    if(!titleRenderBackend->ResetTitleState(&error))throw std::runtime_error("Could not reset title rendering: "+error);
  }''')
    install_session_loader(runtime)


def install_session_loader(runtime):
    loader=runtime/'oot3d_native_direct_aot.cpp'
    patch(loader,'bool PluginQueried = false;','''bool PluginQueried = false;
void* SessionModule=nullptr;
std::map<std::filesystem::path,void*> RetainedTitleModules;
const Oot3dWholeAotProgramV2* SessionWholeProgram=nullptr;
const Oot3dDirectAotProgramV1* SessionDirectProgram=nullptr;
bool SessionWholeQueried=false,SessionDirectQueried=false;''')
    patch(loader,'#include <vector>','#include <vector>\n#include <map>')
    patch(loader,'  static void* module = []() noexcept -> void* {','''  if(SessionModule)return SessionModule;
  SessionModule = []() noexcept -> void* {''')
    patch(loader,'      return dlopen(path.c_str(), RTLD_NOW | RTLD_LOCAL);','''      if(auto found=RetainedTitleModules.find(path);found!=RetainedTitleModules.end())return found->second;
      auto* loaded=dlopen(path.c_str(),RTLD_NOW | RTLD_LOCAL);
      if(loaded)RetainedTitleModules.emplace(path,loaded);
      return loaded;''')
    patch(loader,'  return module;\n}\n#endif\n\ntemplate', '  return SessionModule;\n}\n#endif\n\ntemplate')
    for name,kind in [('Whole','Oot3dWholeAotProgramV2'),('Direct','Oot3dDirectAotProgramV1')]:
        patch(loader,f'  static const {kind} *program = []() noexcept {{',f'''  if(Session{name}Queried)return Session{name}Program;
  Session{name}Queried=true;
  Session{name}Program = []() noexcept {{''')
        # Restrict to this function; both contain the same return text.
        text=loader.read_text();start=text.index(f'const {kind} *{name}AotProgram()');end=text.index('\n}\n',start)+3
        body=text[start:end].replace('  return program;',f'  return Session{name}Program;')
        loader.write_text(text[:start]+body+text[end:])
    patch(loader,'void ConfigureTitlePlugin(const std::filesystem::path& path) {','''void ResetTitlePluginForSession() {
  if(SessionWholeProgram && SessionWholeProgram->ExecutionActive())
    throw std::runtime_error("Cannot replace an executing title");
  SessionModule=nullptr;SessionWholeProgram=nullptr;SessionDirectProgram=nullptr;
  SessionWholeQueried=false;SessionDirectQueried=false;PluginQueried=false;
}

void ConfigureTitlePlugin(const std::filesystem::path& path) {''')
    header=runtime/'triaevum_title_plugin_loader.h'
    patch(header,'void ConfigureTitlePlugin(const std::filesystem::path& path);',
          'void ConfigureTitlePlugin(const std::filesystem::path& path);\nvoid ResetTitlePluginForSession();')

if __name__=='__main__':
    import sys
    install(Path(sys.argv[1]).resolve())
