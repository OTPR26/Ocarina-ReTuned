#include "program_cache.h"
#include <cassert>
#include <filesystem>
#include <fstream>
#include <iostream>
int main(int argc,char**argv) {
    assert(argc==2);
    namespace fs=std::filesystem;
    const fs::path root(argv[1]);fs::create_directories(root);
    RetunedGlCache::Record record{"vertex-source","fragment-source",42,{0,1,2,255}};
    const auto path=root/(RetunedGlCache::Key(record)+".cache");
    assert(RetunedGlCache::Store(root,record));
    RetunedGlCache::Record loaded;
    assert(RetunedGlCache::Load(path,loaded));
    assert(loaded.Vertex==record.Vertex&&loaded.Fragment==record.Fragment&&loaded.Format==42&&loaded.Binary==record.Binary);
    // Same sources but a freshly rebuilt driver binary can replace its cache.
    record.Binary={9,8,7};assert(RetunedGlCache::Store(root,record));
    assert(RetunedGlCache::Load(path,loaded)&&loaded.Binary==record.Binary);
    // A partial write is not a usable program and cannot allocate from a bogus length.
    { std::ofstream out(path,std::ios::binary|std::ios::trunc);out.write("RTGLC001",8);
      RetunedGlCache::WriteWord(out,0xffffffff);RetunedGlCache::WriteWord(out,2);
      RetunedGlCache::WriteWord(out,0);RetunedGlCache::WriteWord(out,0); }
    assert(!RetunedGlCache::Load(path,loaded));
    assert(RetunedGlCache::Store(root,record));
    { std::fstream out(path,std::ios::binary|std::ios::in|std::ios::out);out.seekp(24);out.put('X'); }
    assert(!RetunedGlCache::Load(path,loaded));
    assert(RetunedGlCache::Store(root,record));
    fs::copy_file(path,root/"wrong-key.cache",fs::copy_options::overwrite_existing);
    assert(!RetunedGlCache::Load(root/"wrong-key.cache",loaded));
    fs::resize_file(path,25);assert(!RetunedGlCache::Load(path,loaded));
    { std::ofstream blocked(root/"file-not-directory");blocked<<"keep"; }
    assert(!RetunedGlCache::Store(root/"file-not-directory",record));
    fs::remove_all(root);
    std::cout<<"PASS: cache round-trip, replacement, corruption, truncation, bounded reads, key validation, and write failure\n";
}
