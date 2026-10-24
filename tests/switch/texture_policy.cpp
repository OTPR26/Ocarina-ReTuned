#include "tools/native/switch/deko_backend/texture_policy.h"
#include <cassert>
int main(){
 using namespace RetunedDeko;
 assert(NativeTextureBaseBytes(0,8,8)==256);
 assert(NativeTextureBaseBytes(1,16,8)==384);
 assert(NativeTextureBaseBytes(10,8,8)==32);
 assert(NativeTextureBaseBytes(0,1,1)==256);
 assert(!NativeTextureBaseBytes(14,8,8));
 assert(!NativeTextureBaseBytes(0,0,8));
 assert(!NativeTextureBaseBytes(0,8193,8));
 assert(ReplacementFits(1024,1024,4*1024*1024,0,0));
 assert(ReplacementFits(2048,2048,16*1024*1024,0,0));
 assert(ReplacementFits(4096,4096,64*1024*1024,0,0));
 assert(!ReplacementFits(8192,8192,256*1024*1024,0,0));
 assert(!ReplacementFits(2048,2048,1,0,0));
 assert(!ReplacementFits(2048,2048,16*1024*1024,TextureGpuBudget-1,0));
 assert(!ReplacementFits(1024,1024,4*1024*1024,0,TextureUploadPerFrame));
 assert(ReplacementFits(512,512,1024*1024,0,1024*1024));
}
