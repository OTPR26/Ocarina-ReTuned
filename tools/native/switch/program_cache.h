// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "fast/renderer3ds/pica_shader_source_identity.h"
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

namespace RetunedGlCache {
// Local, disposable, game-derived cache. Never include these files in releases.
constexpr uint32_t MaxSource = 1024 * 1024;
constexpr uint32_t MaxBinary = 8 * 1024 * 1024;
constexpr uint64_t MaxWarmBytes = 128ULL * 1024 * 1024;
constexpr size_t MaxWarmPrograms = 512;
struct Record {
    std::string Vertex, Fragment;
    uint32_t Format = 0;
    std::vector<uint8_t> Binary;
};
inline std::string Identity(std::string_view value) {
    const auto id=Fast::Renderer3ds::IdentifyPicaShaderSource(value);
    return std::to_string(id.Id)+"-"+std::to_string(id.SecondaryHash)+"-"+std::to_string(id.Size);
}
inline std::string Key(const Record& r) { return Identity(r.Vertex)+"_"+Identity(r.Fragment); }
inline bool ReadWord(std::istream& in,uint32_t& value) {
    std::array<unsigned char,4> b{};
    if(!in.read(reinterpret_cast<char*>(b.data()),4)) return false;
    value=uint32_t(b[0])|(uint32_t(b[1])<<8)|(uint32_t(b[2])<<16)|(uint32_t(b[3])<<24);
    return true;
}
inline void WriteWord(std::ostream& out,uint32_t value) {
    const std::array<char,4> b{char(value),char(value>>8),char(value>>16),char(value>>24)};
    out.write(b.data(),4);
}
inline bool Load(const std::filesystem::path& path,Record& result) {
    std::error_code ec;
    const auto size=std::filesystem::file_size(path,ec);
    if(ec || size<24 || size>24ULL+2*MaxSource+MaxBinary+256) return false;
    std::ifstream in(path,std::ios::binary);
    std::array<char,8> magic{};
    uint32_t vs=0,fs=0,bs=0,format=0;
    if(!in.read(magic.data(),8) || magic!=std::array<char,8>{'R','T','G','L','C','0','0','1'} ||
       !ReadWord(in,vs)||!ReadWord(in,fs)||!ReadWord(in,bs)||!ReadWord(in,format) ||
       !vs||!fs||vs>MaxSource||fs>MaxSource||bs>MaxBinary) return false;
    Record r;
    r.Vertex.resize(vs);r.Fragment.resize(fs);r.Binary.resize(bs);r.Format=format;
    if(!in.read(r.Vertex.data(),vs)||!in.read(r.Fragment.data(),fs)||
       (bs&&!in.read(reinterpret_cast<char*>(r.Binary.data()),bs))) return false;
    std::string checksum;
    if(!std::getline(in,checksum) || in.peek()!=std::char_traits<char>::eof()) return false;
    const auto binaryView=std::string_view(reinterpret_cast<const char*>(r.Binary.data()),r.Binary.size());
    if(checksum!=Key(r)+"_"+Identity(binaryView)+"_"+std::to_string(r.Format)) return false;
    if(path.stem().string()!=Key(r)) return false;
    result=std::move(r);
    return true;
}
inline bool Store(const std::filesystem::path& directory,const Record& r) {
    if(r.Vertex.empty()||r.Fragment.empty()||r.Vertex.size()>MaxSource||r.Fragment.size()>MaxSource||r.Binary.size()>MaxBinary) return false;
    std::error_code ec;
    std::filesystem::create_directories(directory,ec);
    if(ec) return false;
    const auto path=directory/(Key(r)+".cache");
    auto temporary=path;temporary+=".new";
    {
        std::ofstream out(temporary,std::ios::binary|std::ios::trunc);
        out.write("RTGLC001",8);
        WriteWord(out,r.Vertex.size());WriteWord(out,r.Fragment.size());WriteWord(out,r.Binary.size());WriteWord(out,r.Format);
        out.write(r.Vertex.data(),r.Vertex.size());out.write(r.Fragment.data(),r.Fragment.size());
        if(!r.Binary.empty())out.write(reinterpret_cast<const char*>(r.Binary.data()),r.Binary.size());
        const auto binaryView=std::string_view(reinterpret_cast<const char*>(r.Binary.data()),r.Binary.size());
        out<<Key(r)<<"_"<<Identity(binaryView)<<"_"<<r.Format<<'\n';
        out.flush();
        if(!out) { out.close();std::filesystem::remove(temporary,ec);return false; }
    }
    // Replacing a disposable cache is safe to retry after interruption. Horizon
    // rename does not replace an existing destination as POSIX rename does.
    std::filesystem::remove(path,ec);
    ec.clear();std::filesystem::rename(temporary,path,ec);
    if(ec) {std::error_code cleanup;std::filesystem::remove(temporary,cleanup);return false;}
    return true;
}
}
