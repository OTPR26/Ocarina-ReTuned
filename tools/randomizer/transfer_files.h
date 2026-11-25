#pragma once
#include <filesystem>
#include <fstream>
#include <cstdio>
#include <stdexcept>
#include <string>

namespace RetunedRandomizer {
inline std::string ReadRunDocument(const std::filesystem::path& path) {
    constexpr auto limit=10*1024*1024;
    if(!std::filesystem::is_regular_file(path) || std::filesystem::is_symlink(path))
        throw std::runtime_error("Choose a randomizer run file");
    const auto size=std::filesystem::file_size(path);
    if(size>limit)throw std::runtime_error("Randomizer run file is too large");
    std::ifstream input(path,std::ios::binary);
    input.exceptions(std::ios::badbit|std::ios::failbit);
    std::string bytes(size,'\0');input.read(bytes.data(),bytes.size());
    if(input.peek()!=std::char_traits<char>::eof())
        throw std::runtime_error("Run file changed while reading");
    return bytes;
}
inline void WriteRunDocument(const std::filesystem::path& path,const std::string& bytes) {
#ifdef _WIN32
    auto* file=_wfopen(path.c_str(),L"wbx");
#else
    auto* file=fopen(path.c_str(),"wbx");
#endif
    if(!file)throw std::runtime_error("Choose a new filename in a writable folder");
    bool ok=fwrite(bytes.data(),1,bytes.size(),file)==bytes.size();
    ok=fclose(file)==0 && ok;
    if(!ok) {
        std::error_code ignored;std::filesystem::remove(path,ignored);
        throw std::runtime_error("Could not finish exporting the run");
    }
}
}
