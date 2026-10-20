#include "texture_aliases.h"
#include <cassert>
#include <unordered_map>
#include <string>
int main(){
 using namespace Oot3d::Renderer;
 std::unordered_map<uint64_t,std::string> index{{1,"original"},{2,"explicit"},{3,"modern"}};
 ApplyTextureHashAliases(index,{{4,1,false},{2,1,false},{5,4,false},{6,3,true}},false);
 assert(index.at(4)=="original" && index.at(2)=="explicit");
 assert(!index.contains(5) && !index.contains(6));
 ApplyTextureHashAliases(index,{{6,3,true}},true);assert(index.at(6)=="modern");
 std::unordered_map<uint64_t,std::string> empty;
 ApplyTextureHashAliases(empty,{{4,1,false}},false);assert(empty.empty());
}
