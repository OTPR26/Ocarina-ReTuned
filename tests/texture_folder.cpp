#include "../tools/frontend/texture_folder.h"
#include <cassert>
int main(){
 using namespace RetunedFrontend;
 assert(!IsTextureDocument("/ordinary/textures/image.png"));
 const std::string path="/app/retuned-texture-links/session/subfolder/image.png";
 assert(IsTextureDocument(path));
 bool missing=false;try{ReadTextureDocument(path);}catch(const std::runtime_error&){missing=true;}assert(missing);
 std::string requested;
 TextureFolders.Read=[&](const std::string& value){requested=value;return std::vector<uint8_t>{1,2,3};};
 assert((ReadTextureDocument(path)==std::vector<uint8_t>{1,2,3}));assert(requested==path);
 TextureFolders.TakeSelection=[]{return std::string("/selected/folder");};
 assert(TextureFolders.TakeSelection()=="/selected/folder");
}
