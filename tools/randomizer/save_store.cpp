#include "save_store.h"
#include <triaevum/sha256.h>
#include <fstream>
#include <stdexcept>
#include <algorithm>
#include <atomic>
#include <cstdio>
#include <cerrno>
#if defined(__SWITCH__) || defined(RETUNED_TEST_FAT_SAVES)
#include <mutex>
#endif
#ifdef _WIN32
#include <io.h>
#define NOMINMAX
#include <windows.h>
#else
#include <unistd.h>
#include <fcntl.h>
#endif

namespace RetunedRandomizer {
namespace {
constexpr std::size_t NativeSize = 0x14dc;
std::string Digest(std::span<const std::uint8_t> bytes) {
    constexpr char hex[]="0123456789abcdef";
    std::string result;
    for(auto b:triaevum::module::detail::Sha256(bytes)) {result+=hex[b>>4];result+=hex[b&15];}
    return result;
}
void CheckHash(const std::string& value) {
    if(value.size()!=64 || value.find_first_not_of("0123456789abcdef")!=std::string::npos)
        throw std::runtime_error("Invalid randomizer identity");
}
Bytes Read(const std::filesystem::path& path, std::size_t expected) {
    if(std::filesystem::is_symlink(path) || std::filesystem::file_size(path)!=expected)
        throw std::runtime_error("Randomizer save record has invalid size or type");
    Bytes bytes(expected);
    std::ifstream in(path,std::ios::binary);
    if(!in.read(reinterpret_cast<char*>(bytes.data()),bytes.size()))
        throw std::runtime_error("Cannot read randomizer save record");
    return bytes;
}
void SyncDirectory(const std::filesystem::path& directory) {
#if !defined(_WIN32) && !defined(__SWITCH__)
    int fd=open(directory.c_str(),O_RDONLY);
    if(fd<0)throw std::runtime_error("Cannot open randomizer save directory");
    const int result=fsync(fd);close(fd);
    if(result)throw std::runtime_error("Cannot sync randomizer save directory");
#endif
}
#if defined(__SWITCH__) || defined(RETUNED_TEST_FAT_SAVES)
std::mutex sdSaveMutex;
void RecoverNative(const std::filesystem::path& path) {
    const auto previous = path.string() + ".previous";
    if (!std::filesystem::exists(previous)) return;
    if (std::filesystem::exists(path)) std::filesystem::remove(previous);
    else std::filesystem::rename(previous, path);
}
#endif
void Publish(const std::filesystem::path& destination, std::span<const std::uint8_t> bytes, bool replace=false) {
    static std::atomic<unsigned long> counter{};
    std::filesystem::path temporary;
    FILE* file=nullptr;
    for(unsigned attempt=0;attempt<1024 && !file;++attempt) {
        temporary=destination;
        temporary += ".partial-"+std::to_string(++counter);
#ifdef _WIN32
        file=_wfopen(temporary.c_str(),L"wbx");
#else
        file=fopen(temporary.c_str(),"wbx");
#endif
        if(!file && errno!=EEXIST)break;
    }
    if(!file)throw std::runtime_error("Cannot create randomizer save record");
    bool ok=fwrite(bytes.data(),1,bytes.size(),file)==bytes.size() && fflush(file)==0;
#ifdef _WIN32
    if(ok)ok=_commit(_fileno(file))==0;
#else
    if(ok)ok=fsync(fileno(file))==0;
#endif
    ok=fclose(file)==0 && ok;
    try {
        if(!ok)throw std::runtime_error("Cannot persist randomizer save record");
#if defined(__SWITCH__) || defined(RETUNED_TEST_FAT_SAVES)
        // SD rename cannot replace a file. Keep the old complete generation
        // until the new native save is visible; recover it on the next launch.
        std::lock_guard lock(sdSaveMutex);
        if (replace) {
            RecoverNative(destination);
            if (std::filesystem::exists(destination))
                std::filesystem::rename(destination, destination.string() + ".previous");
        } else if (std::filesystem::exists(destination)) {
            throw std::runtime_error("Randomizer record already exists");
        }
        try {
            std::filesystem::rename(temporary, destination);
        } catch (...) {
            if (replace) RecoverNative(destination);
            throw;
        }
        if (replace) RecoverNative(destination);
#else
        // Link publishes a complete immutable file without replacing any record.
        if(replace) {
#ifdef _WIN32
            if(!MoveFileExW(temporary.c_str(),destination.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH))
                throw std::runtime_error("Cannot replace randomized native save");
#else
            std::filesystem::rename(temporary,destination);
#endif
        } else std::filesystem::create_hard_link(temporary,destination);
#endif
        SyncDirectory(destination.parent_path());
        std::filesystem::remove(temporary);
    } catch(...) {std::error_code ignored;std::filesystem::remove(temporary,ignored);throw;}
}
}
SaveStore::SaveStore(std::filesystem::path directory, std::string seedHash,
                     std::string runtimeHash,std::size_t extendedSize,bool create)
    :directory_(std::move(directory)),extendedSize_(extendedSize) {
    CheckHash(seedHash);CheckHash(runtimeHash);
    if(!extendedSize || extendedSize>1024*1024)throw std::runtime_error("Invalid extended save ABI");
    const auto identity="retuned-randomizer-save-v1\n"+seedHash+"\n"+runtimeHash+"\n"+std::to_string(extendedSize)+"\n";
    identity_=Bytes(identity.begin(),identity.end());
    if(create) {
        if(!std::filesystem::create_directory(directory_))throw std::runtime_error("Randomizer profile already exists");
        Publish(directory_/"identity",identity_);
        SyncDirectory(directory_.parent_path().empty()?std::filesystem::path("."):directory_.parent_path());
    }
    if(std::filesystem::is_symlink(directory_) || Read(directory_/"identity",identity_.size())!=identity_)
        throw std::runtime_error("Randomizer seed/runtime identity mismatch");
#if defined(__SWITCH__) || defined(RETUNED_TEST_FAT_SAVES)
    std::lock_guard lock(sdSaveMutex);
    for (unsigned slot = 0; slot < 3; ++slot)
        RecoverNative(directory_ / "native" / ("save0" + std::to_string(slot) + ".bin"));
#endif
}
std::filesystem::path SaveStore::Record(unsigned slot,std::span<const std::uint8_t> native) const {
    if(slot>=3 || native.size()!=NativeSize)throw std::runtime_error("Invalid randomizer save slot or native size");
    return directory_/("slot"+std::to_string(slot)+"-"+Digest(native)+".state");
}
void SaveStore::BeforeWrite(unsigned slot,std::span<const std::uint8_t> native,
                            std::span<const std::uint8_t> extended) {
    const auto path=Record(slot,native);
    if(extended.size()!=extendedSize_)throw std::runtime_error("Invalid extended save size");
    if(std::filesystem::exists(path)) {
        const auto old=Load(slot,native);
        if(!std::equal(old.begin(),old.end(),extended.begin()))
            throw std::runtime_error("Native save matches a different extended state; refusing ambiguous save");
        SyncDirectory(directory_);
        return;
    }
    Bytes record=identity_;
    record.insert(record.end(),native.begin(),native.end());
    record.insert(record.end(),extended.begin(),extended.end());
    const auto hash=Digest(record);record.insert(record.end(),hash.begin(),hash.end());
    Publish(path,record);
}
void SaveStore::Commit(unsigned slot,std::span<const std::uint8_t> native,
                       std::span<const std::uint8_t> extended) {
    BeforeWrite(slot,native,extended);
    const auto directory=directory_/"native";
    if(std::filesystem::is_symlink(directory))throw std::runtime_error("Invalid native save directory");
    std::filesystem::create_directory(directory);
    SyncDirectory(directory_);
    const auto path=directory/("save0"+std::to_string(slot)+".bin");
    if(std::filesystem::is_symlink(path))throw std::runtime_error("Invalid native save path");
    Publish(path,native,true);
}
Bytes SaveStore::Load(unsigned slot,std::span<const std::uint8_t> native) const {
    auto record=Read(Record(slot,native),identity_.size()+NativeSize+extendedSize_+64);
    const auto checksum=Digest(std::span(record).first(record.size()-64));
    if(!std::equal(checksum.begin(),checksum.end(),record.end()-64) ||
       !std::equal(identity_.begin(),identity_.end(),record.begin()) ||
       !std::equal(native.begin(),native.end(),record.begin()+identity_.size()))
        throw std::runtime_error("Randomizer save record is corrupt or belongs to another seed");
    return Bytes(record.begin()+identity_.size()+NativeSize,record.end()-64);
}
}
