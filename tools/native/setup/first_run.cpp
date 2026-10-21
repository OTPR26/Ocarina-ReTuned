#include "first_run.h"
#include <SDL.h>
#include <imgui.h>
#include <imgui_impl_sdl2.h>
#include <imgui_impl_opengl3.h>
#include <nlohmann/json.hpp>
#include "fast/oot3d/retuned_interface_font.h"
#include "fast/oot3d/retuned_artwork.h"
#include <stb_image.h>
#include <atomic>
#include <algorithm>
#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#if defined(__APPLE__)
#include <OpenGL/gl3.h>
#else
#include <GL/glew.h>
#endif
#if defined(_WIN32)
#include <windows.h>
#include <commdlg.h>
#else
#include <spawn.h>
#include <sys/wait.h>
#include <unistd.h>
extern char** environ;
#endif

namespace {
using Path = std::filesystem::path;
using Json = nlohmann::json;
std::string Text(const Path& path) { auto s=path.u8string();return {s.begin(),s.end()}; }
Path FromText(const std::string& s) {return Path(std::u8string(s.begin(),s.end()));}
Json Read(const Path& p) {std::ifstream f(p);return Json::parse(f);}
Path DefaultRoot() {
#if defined(_WIN32)
    const char* base=std::getenv("LOCALAPPDATA");
    if(!base)throw std::runtime_error("Windows app data directory is unavailable");
    return FromText(base)/"Ocarina ReTuned";
#elif defined(__APPLE__)
    const char* base=std::getenv("HOME");
    if(!base)throw std::runtime_error("User home directory is unavailable");
    return Path(base)/"Library/Application Support/Ocarina ReTuned";
#else
    if(const char* base=std::getenv("XDG_DATA_HOME"))return Path(base)/"Ocarina ReTuned";
    const char* base=std::getenv("HOME");
    if(!base)throw std::runtime_error("User home directory is unavailable");
    return Path(base)/".local/share/Ocarina ReTuned";
#endif
}
#if defined(_WIN32)
std::wstring Quote(const std::wstring& value) {
    std::wstring out=L"\"";unsigned slashes=0;
    for(wchar_t ch:value){if(ch==L'\\'){++slashes;continue;}
        out.append(ch==L'"'?slashes*2+1:slashes,L'\\');out+=ch;slashes=0;}
    out.append(slashes*2,L'\\');return out+L'"';
}
#endif
int Run(const std::vector<std::string>& arguments) {
#if defined(_WIN32)
    std::wstring command;
    for(auto& a:arguments){if(!command.empty())command+=L' ';command+=Quote(FromText(a).wstring());}
    STARTUPINFOW startup{};startup.cb=sizeof(startup);PROCESS_INFORMATION process{};
    if(!CreateProcessW(nullptr,command.data(),nullptr,nullptr,FALSE,CREATE_NO_WINDOW,nullptr,nullptr,&startup,&process))return -1;
    WaitForSingleObject(process.hProcess,INFINITE);DWORD result=1;GetExitCodeProcess(process.hProcess,&result);
    CloseHandle(process.hThread);CloseHandle(process.hProcess);return static_cast<int>(result);
#else
    std::vector<char*> argv;for(auto& a:arguments)argv.push_back(const_cast<char*>(a.c_str()));argv.push_back(nullptr);
    pid_t pid;int result=posix_spawnp(&pid,argv[0],nullptr,nullptr,argv.data(),environ);if(result)return result;
    int status=0;while(waitpid(pid,&status,0)<0){if(errno!=EINTR)return -1;}
    return WIFEXITED(status)?WEXITSTATUS(status):-1;
#endif
}
std::string ChooseRom() {
#if defined(_WIN32)
    wchar_t file[32768]{};OPENFILENAMEW dialog{};dialog.lStructSize=sizeof(dialog);
    dialog.lpstrFile=file;dialog.nMaxFile=32768;dialog.lpstrFilter=L"Cartridge dumps\0*.3ds;*.cci\0All files\0*.*\0";
    dialog.Flags=OFN_FILEMUSTEXIST|OFN_NOCHANGEDIR;
    return GetOpenFileNameW(&dialog)?Text(Path(file)):std::string{};
#else
#if defined(__APPLE__)
    const char* command="osascript -e 'POSIX path of (choose file with prompt \"Choose your decrypted Ocarina of Time 3D ROM\")' 2>/dev/null";
#else
    const char* command="zenity --file-selection --title='Choose your decrypted Ocarina of Time 3D ROM' 2>/dev/null";
#endif
    FILE* pipe=popen(command,"r");if(!pipe)return {};std::string result;char part[4096];
    while(fgets(part,sizeof(part),pipe))result+=part;
    int status=pclose(pipe);if(status)return {};while(!result.empty()&&(result.back()=='\n'||result.back()=='\r'))result.pop_back();return result;
#endif
}
}

bool RetunedFirstRun(int argc,char** argv,Path& profile) {
    if(argc==1)profile=DefaultRoot()/"native-launch.json";
    else if(argc==3&&std::string(argv[1])=="--launch-profile")profile=FromText(argv[2]);
    else return true;
    if(std::filesystem::is_regular_file(profile)) {
        try {
            const auto arguments=Read(profile).at("arguments").get<std::vector<std::string>>();
            bool ready=true;
            for(const char* flag:{"--a32-process-manifest","--title-plugin"}) {
                auto found=std::find(arguments.begin(),arguments.end(),flag);
                if(found==arguments.end()||++found==arguments.end()||!std::filesystem::is_regular_file(FromText(*found)))ready=false;
            }
            if(ready)return true;
        }catch(...){}
    }
    const Path root=std::filesystem::absolute(profile).parent_path();
    // A preparation kit is installed beside the neutral host. No private title
    // or game assets belong in it. Development can select a local kit explicitly.
    Path kit;
    if(const char* value=std::getenv("RETUNED_SETUP_KIT"))kit=FromText(value);
    else {
        char* base=SDL_GetBasePath();Path executable=base?Path(base):Path{};SDL_free(base);
#if defined(__APPLE__)
        kit=executable/"../Resources/setup/kit.json";
#else
        kit=executable/"setup/kit.json";
#endif
    }
    std::string status="Choose your decrypted Ocarina of Time 3D USA ROM (.3ds or .cci).";
    const bool hasKit=std::filesystem::is_regular_file(kit);
    if(!hasKit)status="The ROM preparation tools are missing from this preview. Install the preparation kit before continuing.";
    if(SDL_Init(SDL_INIT_VIDEO|SDL_INIT_GAMECONTROLLER)!=0)throw std::runtime_error(SDL_GetError());
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_FLAGS,SDL_GL_CONTEXT_FORWARD_COMPATIBLE_FLAG);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_CORE);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,3);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,2);
    SDL_Window* window=SDL_CreateWindow("Ocarina ReTuned - Setup",SDL_WINDOWPOS_CENTERED,SDL_WINDOWPOS_CENTERED,960,600,SDL_WINDOW_OPENGL|SDL_WINDOW_RESIZABLE|SDL_WINDOW_ALLOW_HIGHDPI);
    if(!window){SDL_Quit();throw std::runtime_error(SDL_GetError());}
    SDL_SetWindowMinimumSize(window,760,540);
    auto context=SDL_GL_CreateContext(window);
    if(!context){SDL_DestroyWindow(window);SDL_Quit();throw std::runtime_error(SDL_GetError());}
#if !defined(__APPLE__)
    glewExperimental=GL_TRUE;glewInit();
#endif
    SDL_GL_SetSwapInterval(1);ImGui::CreateContext();auto& io=ImGui::GetIO();
    io.ConfigFlags|=ImGuiConfigFlags_NavEnableKeyboard|ImGuiConfigFlags_NavEnableGamepad;
    int pixelWidth,pixelHeight,width,height;SDL_GL_GetDrawableSize(window,&pixelWidth,&pixelHeight);SDL_GetWindowSize(window,&width,&height);
    const float density=static_cast<float>(pixelWidth)/width;
    ImFontConfig font;font.FontDataOwnedByAtlas=false;
    const ImWchar ranges[]={0x20,0xFF,0x2000,0x206F,0};
    io.Fonts->AddFontFromMemoryTTF(RetunedFrontend::InterfaceFont,sizeof(RetunedFrontend::InterfaceFont),22*density,&font,ranges);
    ImFont* heading=io.Fonts->AddFontFromMemoryTTF(RetunedFrontend::InterfaceBold,sizeof(RetunedFrontend::InterfaceBold),40*density,&font,ranges);
    io.FontGlobalScale=1/density;
    ImGui_ImplSDL2_InitForOpenGL(window,context);ImGui_ImplOpenGL3_Init("#version 150");
    auto& style=ImGui::GetStyle();style.WindowRounding=0;style.FrameRounding=10;style.FramePadding={18,14};
    style.Colors[ImGuiCol_WindowBg]={0,0,0,1};style.Colors[ImGuiCol_Text]={.95f,.96f,1,1};
    style.Colors[ImGuiCol_Button]={.08f,.17f,.30f,1};style.Colors[ImGuiCol_ButtonHovered]={.12f,.28f,.48f,1};style.Colors[ImGuiCol_ButtonActive]={.16f,.35f,.58f,1};
    GLuint art=0;int artWidth=0,artHeight=0,components=0;
    if(auto* pixels=stbi_load_from_memory(RetunedFrontend::OcarinaArtwork,sizeof(RetunedFrontend::OcarinaArtwork),&artWidth,&artHeight,&components,4)){
        glGenTextures(1,&art);glBindTexture(GL_TEXTURE_2D,art);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,artWidth,artHeight,0,GL_RGBA,GL_UNSIGNED_BYTE,pixels);stbi_image_free(pixels);
    }
    std::atomic<bool> running=false,finished=false;std::atomic<int> result=1;std::thread worker;
    bool close=false,success=false;std::string selected;char pathText[8192]{};Path progress=root/"setup-progress.json", cancel=root/"setup-cancel";
    SDL_GameController* controller=nullptr;
    for(int i=0;i<SDL_NumJoysticks();++i)if(SDL_IsGameController(i)){controller=SDL_GameControllerOpen(i);if(controller)break;}
    while(!close) {
        SDL_Event event;while(SDL_PollEvent(&event)){ImGui_ImplSDL2_ProcessEvent(&event);
            if(event.type==SDL_QUIT&&!running)close=true;
            if(event.type==SDL_DROPFILE){if(!running){selected=event.drop.file;std::snprintf(pathText,sizeof(pathText),"%s",selected.c_str());}SDL_free(event.drop.file);}}
        if(running){try {status=Read(progress).at("message").get<std::string>();}catch(...){} }
        if(finished.exchange(false)){running=false;if(worker.joinable())worker.join();success=result==0&&std::filesystem::is_regular_file(profile);if(success)close=true;else if(status.empty())status="Setup did not finish. Your existing files are unchanged.";}
        ImGui_ImplOpenGL3_NewFrame();ImGui_ImplSDL2_NewFrame();ImGui::NewFrame();
        ImGui::SetNextWindowPos({0,0});ImGui::SetNextWindowSize(io.DisplaySize);
        ImGui::Begin("Setup",nullptr,ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoMove|ImGuiWindowFlags_NoSavedSettings);
        const float margin=40;ImGui::SetCursorPos({margin,50});ImGui::PushFont(heading);ImGui::TextUnformatted("Ocarina ReTuned");ImGui::PopFont();
        if(art){ImGui::SetCursorPos({io.DisplaySize.x-180,35});ImGui::Image((ImTextureID)(intptr_t)art,{140,140});}
        ImGui::SetCursorPos({margin,120});ImGui::TextUnformatted("First-time setup");ImGui::Spacing();
        ImGui::SetCursorPosX(margin);ImGui::PushTextWrapPos(io.DisplaySize.x-margin);ImGui::TextUnformatted(status.c_str());ImGui::PopTextWrapPos();
        ImGui::SetCursorPos({margin,240});ImGui::BeginDisabled(running||!hasKit);ImGui::SetNextItemWidth(io.DisplaySize.x-margin*2);ImGui::InputTextWithHint("##rom","ROM file - choose or drag it here",pathText,sizeof(pathText));
        ImGui::SetCursorPosX(margin);
        if(ImGui::Button("Choose ROM...")){auto chosen=ChooseRom();if(!chosen.empty())std::snprintf(pathText,sizeof(pathText),"%s",chosen.c_str());}
        ImGui::SameLine();ImGui::BeginDisabled(!pathText[0]);if(ImGui::Button("Prepare game")){
            try {
                const auto metadata=Read(kit);const auto base=std::filesystem::absolute(kit).parent_path();
                const auto resolve=[&](const char* name){return Text(base/FromText(metadata.at(name).get<std::string>()));};
                auto arguments=std::vector<std::string>{resolve("python"),resolve("script"),"--kit",Text(std::filesystem::absolute(kit)),"--rom",pathText,"--data-root",Text(root),"--progress-file",Text(progress),"--cancel-file",Text(cancel)};
                std::filesystem::create_directories(root);std::filesystem::remove(progress);std::filesystem::remove(cancel);running=true;status="Starting local preparation...";
                worker=std::thread([&,arguments]{result=Run(arguments);finished=true;});
            }catch(const std::exception& e){status=e.what();}
        }ImGui::EndDisabled();ImGui::EndDisabled();
        ImGui::SetCursorPos({margin,io.DisplaySize.y-115});ImGui::PushTextWrapPos(io.DisplaySize.x-margin);ImGui::TextDisabled("Preparation stays on your computer. Saves and controller settings are preserved.\nThe first build can take several minutes and requires local C++ build tools.");ImGui::PopTextWrapPos();
        ImGui::SetCursorPosX(margin);
        if(running){if(ImGui::Button("Cancel setup")){std::ofstream request(cancel);request<<"cancel";status="Cancelling after the current preparation step...";}}
        else if(ImGui::Button("Close"))close=true;
        ImGui::End();
        ImGui::Render();SDL_GL_GetDrawableSize(window,&pixelWidth,&pixelHeight);glViewport(0,0,pixelWidth,pixelHeight);glClearColor(0,0,0,1);glClear(GL_COLOR_BUFFER_BIT);ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());SDL_GL_SwapWindow(window);
    }
    if(worker.joinable())worker.join();std::filesystem::remove(cancel);if(controller)SDL_GameControllerClose(controller);
    if(art)glDeleteTextures(1,&art);
    ImGui_ImplOpenGL3_Shutdown();ImGui_ImplSDL2_Shutdown();ImGui::DestroyContext();SDL_GL_DeleteContext(context);SDL_DestroyWindow(window);SDL_Quit();return success;
}
