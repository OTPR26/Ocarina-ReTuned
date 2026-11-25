#include "generator.h"
#include <filesystem>
#include <fstream>
#include <iostream>
int main(int argc,char** argv) {
    try {
        if(argc!=3)throw std::runtime_error("Usage: retuned-seed SEED NEW_OUTPUT_DIRECTORY");
        const std::filesystem::path output=argv[2];
        // A unique destination prevents replacing any existing run or saves.
        if(!std::filesystem::create_directory(output))throw std::runtime_error("Output directory already exists");
        try {
            const auto json=RetunedRandomizer::Generate(argv[1],[](unsigned n){std::cerr<<"Placement attempt "<<n<<"\n";});
            const auto partial=output/"seed.json.partial";
            {std::ofstream f(partial,std::ios::binary);f.exceptions(std::ios::badbit|std::ios::failbit);f<<json;f.close();}
            std::filesystem::rename(partial,output/"seed.json");
            std::cerr<<"Seed generated. Runtime integration is not yet enabled.\n";
        } catch(...) {std::filesystem::remove(output/"seed.json.partial");std::filesystem::remove(output);throw;}
        return 0;
    } catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
