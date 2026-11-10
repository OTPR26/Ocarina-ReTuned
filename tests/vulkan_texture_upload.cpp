#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <map>
#include <span>
#include <stdexcept>
#include <utility>
#include <vector>
using VkDeviceSize = uint64_t;
using VkBuffer = uint64_t;
constexpr unsigned VK_BUFFER_USAGE_TRANSFER_SRC_BIT=1;
constexpr unsigned VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT=2;
constexpr unsigned VK_MEMORY_PROPERTY_HOST_COHERENT_BIT=4;
class GfxRenderingAPIVulkan {
public:
 struct BufferAllocation { VkBuffer Buffer; VkDeviceSize Size; void* Mapped; };
 struct Frame { std::vector<BufferAllocation> TextureUploadBuffers; VkDeviceSize TextureUploadBytesUsed=0; };
 std::array<Frame,2> mFrameResources;
 unsigned mCurrentFrame=0;
 std::map<VkBuffer,std::vector<uint8_t>> live;
 uint64_t next=1; bool fail=false;
 BufferAllocation CreateBuffer(VkDeviceSize size,unsigned usage,unsigned memory,bool mapped) {
  assert(usage==1 && memory==6 && mapped);
  if(fail)throw std::bad_alloc();
  auto id=next++;auto& data=live[id];data.resize(size);return {id,size,data.data()};
 }
 void DestroyBuffer(BufferAllocation& b){assert(live.erase(b.Buffer)==1);b={};}
 std::pair<VkBuffer,VkDeviceSize> StageNativePicaTexture(std::span<const uint8_t>);
 void ResetNativePicaTextureUploads(uint32_t);
};
#include "../tools/native/vulkan_texture_upload.inc"
int main(){
 GfxRenderingAPIVulkan gpu;
 std::vector<uint8_t> small(17,0x31),large(9*1024*1024,0x72);
 auto a=gpu.StageNativePicaTexture(small),b=gpu.StageNativePicaTexture(small);
 assert(a.first==b.first && a.second==0 && b.second==32);
 // A burst larger than the old 64 MiB shared arena must keep every source intact.
 std::vector<std::pair<VkBuffer,VkDeviceSize>> copies;
 for(int i=0;i<9;i++)copies.push_back(gpu.StageNativePicaTexture(large));
 assert(gpu.live.size()==10);
 for(auto [id,offset]:copies)assert(gpu.live.at(id).at(offset)==0x72 && gpu.live.at(id).back()==0x72);
 assert(gpu.live.at(a.first)[0]==0x31);
 gpu.mCurrentFrame=1;
 auto other=gpu.StageNativePicaTexture(small);
 gpu.ResetNativePicaTextureUploads(0);
 assert(gpu.live.size()==2 && gpu.live.contains(other.first));
 gpu.mCurrentFrame=0;
 auto reused=gpu.StageNativePicaTexture(small);
 assert(reused==a);
 // Failed growth preserves pending sources and the cursor.
 gpu.fail=true;auto used=gpu.mFrameResources[0].TextureUploadBytesUsed;
 try{gpu.StageNativePicaTexture(large);assert(false);}catch(const std::bad_alloc&){}
 assert(gpu.mFrameResources[0].TextureUploadBytesUsed==used && gpu.live.size()==2);
 gpu.fail=false;
 // A lone oversize allocation is released after completion, not retained forever.
 gpu.ResetNativePicaTextureUploads(1);
 auto& frame=gpu.mFrameResources[1];gpu.DestroyBuffer(frame.TextureUploadBuffers[0]);frame.TextureUploadBuffers.clear();
 gpu.mCurrentFrame=1;gpu.StageNativePicaTexture(large);gpu.ResetNativePicaTextureUploads(1);
 assert(frame.TextureUploadBuffers.empty() && gpu.live.size()==1);
 gpu.DestroyBuffer(gpu.mFrameResources[0].TextureUploadBuffers[0]);
}
