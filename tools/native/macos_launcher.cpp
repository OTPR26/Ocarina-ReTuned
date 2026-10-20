// SPDX-License-Identifier: GPL-2.0-or-later
// The provisioned app is the native executable. Re-exec it once after setting
// loader paths, preserving its identity and CloudKit provisioning on macOS.
#include <mach-o/dyld.h>
#include <unistd.h>
#include <filesystem>
#include <vector>
#include <string>
#include <cstdlib>
#include <cstdio>
int RetunedMacNativeMain(int argc,char** argv);
int main(int argc, char** argv) {
    if(std::getenv("RETUNED_MAC_BOOTSTRAPPED"))return RetunedMacNativeMain(argc,argv);
    uint32_t size=0;_NSGetExecutablePath(nullptr,&size);
    std::vector<char> executable(size);
    if(_NSGetExecutablePath(executable.data(),&size)!=0)return 1;
    const auto contents=std::filesystem::weakly_canonical(executable.data()).parent_path().parent_path();
    const char* home=std::getenv("HOME");if(!home)return 1;
    const auto data=std::filesystem::path(home)/"Library/Application Support/Ocarina ReTuned";
    std::error_code error;std::filesystem::create_directories(data,error);
    if(error || chdir(data.c_str())!=0)return 1;
    setenv("VK_ICD_FILENAMES",(contents/"Resources/vulkan/icd.d/MoltenVK_icd.json").c_str(),1);
    setenv("DYLD_LIBRARY_PATH",(contents/"Frameworks").c_str(),1);
    setenv("RETUNED_MAC_BOOTSTRAPPED","1",1);
    std::vector<std::string> args={(contents/"MacOS/retuned-native").string()};
    if(argc==1){args.emplace_back("--launch-profile");args.push_back((data/"native-launch.json").string());}
    for(int i=1;i<argc;++i)args.emplace_back(argv[i]);
    std::vector<char*> pointers;for(auto& arg:args)pointers.push_back(arg.data());pointers.push_back(nullptr);
    execv(pointers[0],pointers.data());std::perror("Could not start Ocarina ReTuned");return 1;
}
