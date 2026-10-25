// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#ifdef __ANDROID__
#include "android_display_state.h"
#include <android/native_window.h>
#include <android/native_window_jni.h>
#include <vulkan/vulkan_android.h>
#include <mutex>
#include <vector>
#include <stdexcept>
#include <algorithm>
#include <cstdio>
namespace RetunedFrontend {
inline std::mutex AndroidSurfaceMutex;
inline ANativeWindow* AndroidLowerWindow=nullptr;
inline unsigned AndroidSurfaceGeneration=0;
inline void AndroidSetLowerSurface(JNIEnv* env,jobject surface) {
 std::lock_guard lock(AndroidSurfaceMutex);
 if(AndroidLowerWindow)ANativeWindow_release(AndroidLowerWindow);
 AndroidLowerWindow=surface?ANativeWindow_fromSurface(env,surface):nullptr;
 ++AndroidSurfaceGeneration;AndroidLowerTouch=0;AndroidLowerAvailable=AndroidLowerWindow!=nullptr;
}
class AndroidSecondarySwapchain {
 VkInstance Instance{};VkPhysicalDevice physicalDevice{};VkDevice Device{};ANativeWindow* Window{};unsigned Generation{};
 VkSurfaceKHR Surface{};VkSwapchainKHR Swapchain{};VkFence AcquireFence{};
 VkFormat Format{};VkSurfaceCapabilitiesKHR Capabilities{};int WindowWidth=0,WindowHeight=0;std::vector<VkImage> Images;std::vector<VkImageView> Views;
 std::vector<VkFramebuffer> Frames;std::vector<VkImage> Depth;std::vector<VkImageView> DepthViews;std::vector<VkDeviceMemory> DepthMemory;std::vector<bool> Initialized;
 bool Acquired=false;uint64_t Frame=0;
 static void Check(VkResult r,const char* what){if(r!=VK_SUCCESS)throw std::runtime_error(std::string("Lower display ")+what+": "+std::to_string(r));}
 public:
 VkExtent2D Extent{};uint32_t Index=0;
 VkImage Image()const{return Images.at(Index);} VkImageView View()const{return Views.at(Index);}
 VkFramebuffer Framebuffer()const{return Frames.at(Index);}
 void Destroy() {
  if(Device){vkDeviceWaitIdle(Device);for(auto f:Frames)vkDestroyFramebuffer(Device,f,nullptr);
   for(auto v:Views)vkDestroyImageView(Device,v,nullptr);
   for(auto v:DepthViews)vkDestroyImageView(Device,v,nullptr);
   for(auto i:Depth)vkDestroyImage(Device,i,nullptr);
   for(auto m:DepthMemory)vkFreeMemory(Device,m,nullptr);
   if(AcquireFence)vkDestroyFence(Device,AcquireFence,nullptr);
   if(Swapchain)vkDestroySwapchainKHR(Device,Swapchain,nullptr);}
  if(Surface)vkDestroySurfaceKHR(Instance,Surface,nullptr);
  if(Window)ANativeWindow_release(Window);
  Instance={};Device={};Window=nullptr;Surface={};Swapchain={};AcquireFence={};
  Images.clear();Views.clear();Frames.clear();Depth.clear();DepthViews.clear();DepthMemory.clear();Initialized.clear();Acquired=false;
 }
 bool Acquire(VkInstance instance,VkPhysicalDevice physical,VkDevice device,uint32_t family,
              VkFormat format,VkFormat depthFormat,VkRenderPass renderPass,VkCommandBuffer cmd,uint64_t frame) {
  if(Acquired)return Frame==frame;
  ANativeWindow* window;unsigned generation;
  {std::lock_guard lock(AndroidSurfaceMutex);window=AndroidLowerWindow;generation=AndroidSurfaceGeneration;if(window)ANativeWindow_acquire(window);}
  if(!window){if(Device)Destroy();return false;}
  const bool resize=Window&&(ANativeWindow_getWidth(window)!=WindowWidth||ANativeWindow_getHeight(window)!=WindowHeight);
  if(Device&&(Generation!=generation||Format!=format||resize))Destroy();
  if(!Device){
   Instance=instance;physicalDevice=physical;Device=device;Window=window;Generation=generation;Format=format;
   WindowWidth=ANativeWindow_getWidth(window);WindowHeight=ANativeWindow_getHeight(window);
   VkAndroidSurfaceCreateInfoKHR surface{VK_STRUCTURE_TYPE_ANDROID_SURFACE_CREATE_INFO_KHR};surface.window=window;
   auto create=reinterpret_cast<PFN_vkCreateAndroidSurfaceKHR>(vkGetInstanceProcAddr(instance,"vkCreateAndroidSurfaceKHR"));
   if(!create)throw std::runtime_error("Android Vulkan presentation extension unavailable");
   Check(create(instance,&surface,nullptr,&Surface),"surface creation");
   VkBool32 supported=false;Check(vkGetPhysicalDeviceSurfaceSupportKHR(physical,family,Surface,&supported),"queue support");
   if(!supported)throw std::runtime_error("Graphics queue cannot present lower display");
   VkSurfaceCapabilitiesKHR caps{};Check(vkGetPhysicalDeviceSurfaceCapabilitiesKHR(physical,Surface,&caps),"capabilities");
   Capabilities=caps;
   uint32_t count=0;Check(vkGetPhysicalDeviceSurfaceFormatsKHR(physical,Surface,&count,nullptr),"formats");std::vector<VkSurfaceFormatKHR> formats(count);
   Check(vkGetPhysicalDeviceSurfaceFormatsKHR(physical,Surface,&count,formats.data()),"formats");
   auto selected=std::find_if(formats.begin(),formats.end(),[&](auto f){return f.format==format;});
   if(selected==formats.end())throw std::runtime_error("Lower display lacks matching Vulkan color format");
   if(!(caps.supportedUsageFlags&VK_IMAGE_USAGE_TRANSFER_DST_BIT))throw std::runtime_error("Lower display cannot clear its swapchain");
   Extent=caps.currentExtent;
   if(Extent.width==UINT32_MAX)Extent={std::clamp(uint32_t(ANativeWindow_getWidth(window)),caps.minImageExtent.width,caps.maxImageExtent.width),std::clamp(uint32_t(ANativeWindow_getHeight(window)),caps.minImageExtent.height,caps.maxImageExtent.height)};
   VkSwapchainCreateInfoKHR ci{VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR};ci.surface=Surface;ci.minImageCount=std::max(2u,caps.minImageCount);
   if(caps.maxImageCount)ci.minImageCount=std::min(ci.minImageCount,caps.maxImageCount);
   ci.imageFormat=format;ci.imageColorSpace=selected->colorSpace;ci.imageExtent=Extent;ci.imageArrayLayers=1;
   ci.imageUsage=VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT|VK_IMAGE_USAGE_TRANSFER_DST_BIT;ci.imageSharingMode=VK_SHARING_MODE_EXCLUSIVE;
   ci.preTransform=(caps.supportedTransforms&VK_SURFACE_TRANSFORM_IDENTITY_BIT_KHR)?VK_SURFACE_TRANSFORM_IDENTITY_BIT_KHR:caps.currentTransform;ci.compositeAlpha=(caps.supportedCompositeAlpha&VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR)?VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR:VkCompositeAlphaFlagBitsKHR(caps.supportedCompositeAlpha&-caps.supportedCompositeAlpha);
   ci.presentMode=VK_PRESENT_MODE_FIFO_KHR;ci.clipped=VK_TRUE;Check(vkCreateSwapchainKHR(device,&ci,nullptr,&Swapchain),"swapchain creation");
   Check(vkGetSwapchainImagesKHR(device,Swapchain,&count,nullptr),"images");Images.resize(count);Check(vkGetSwapchainImagesKHR(device,Swapchain,&count,Images.data()),"images");
   Views.resize(count);Frames.resize(count);Depth.resize(count);DepthViews.resize(count);DepthMemory.resize(count);Initialized.resize(count,false);
   if(!renderPass)throw std::runtime_error("Lower display requires the native color/depth render pass");
   for(unsigned i=0;i<count;++i){VkImageViewCreateInfo vi{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};vi.image=Images[i];vi.viewType=VK_IMAGE_VIEW_TYPE_2D;vi.format=format;vi.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};Check(vkCreateImageView(device,&vi,nullptr,&Views[i]),"image view");
    VkImageCreateInfo di{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};di.imageType=VK_IMAGE_TYPE_2D;di.format=depthFormat;di.extent={Extent.width,Extent.height,1};di.mipLevels=1;di.arrayLayers=1;di.samples=VK_SAMPLE_COUNT_1_BIT;di.tiling=VK_IMAGE_TILING_OPTIMAL;di.usage=VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT;
    Check(vkCreateImage(device,&di,nullptr,&Depth[i]),"depth image");VkMemoryRequirements requirements{};vkGetImageMemoryRequirements(device,Depth[i],&requirements);
    VkPhysicalDeviceMemoryProperties memory{};vkGetPhysicalDeviceMemoryProperties(physical,&memory);unsigned type=memory.memoryTypeCount;
    for(unsigned t=0;t<memory.memoryTypeCount;++t)if((requirements.memoryTypeBits&(1u<<t))&&(memory.memoryTypes[t].propertyFlags&VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT)){type=t;break;}
    if(type==memory.memoryTypeCount)throw std::runtime_error("Lower display lacks device-local depth memory");
    VkMemoryAllocateInfo allocation{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};allocation.allocationSize=requirements.size;allocation.memoryTypeIndex=type;Check(vkAllocateMemory(device,&allocation,nullptr,&DepthMemory[i]),"depth memory");Check(vkBindImageMemory(device,Depth[i],DepthMemory[i],0),"depth binding");
    vi.image=Depth[i];vi.format=depthFormat;vi.subresourceRange.aspectMask=VK_IMAGE_ASPECT_DEPTH_BIT;
    if(depthFormat==VK_FORMAT_D24_UNORM_S8_UINT||depthFormat==VK_FORMAT_D32_SFLOAT_S8_UINT)vi.subresourceRange.aspectMask|=VK_IMAGE_ASPECT_STENCIL_BIT;
    Check(vkCreateImageView(device,&vi,nullptr,&DepthViews[i]),"depth view");
    const VkImageView attachments[]{Views[i],DepthViews[i]};
    VkFramebufferCreateInfo fi{VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO};fi.renderPass=renderPass;fi.attachmentCount=2;fi.pAttachments=attachments;fi.width=Extent.width;fi.height=Extent.height;fi.layers=1;Check(vkCreateFramebuffer(device,&fi,nullptr,&Frames[i]),"framebuffer");}
   VkFenceCreateInfo fence{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};Check(vkCreateFence(device,&fence,nullptr,&AcquireFence),"acquire fence");
   std::fprintf(stderr,"RETUNED_LOWER_DISPLAY created width=%u height=%u images=%u\n",Extent.width,Extent.height,count);
  }else ANativeWindow_release(window);
  Check(vkResetFences(device,1,&AcquireFence),"reset acquire fence");
  auto result=vkAcquireNextImageKHR(device,Swapchain,100000000ULL,VK_NULL_HANDLE,AcquireFence,&Index);
  if(result==VK_TIMEOUT||result==VK_NOT_READY)return false;
  if(result==VK_ERROR_OUT_OF_DATE_KHR){Destroy();return false;}
  if(result!=VK_SUCCESS&&result!=VK_SUBOPTIMAL_KHR)Check(result,"acquire");
  Check(vkWaitForFences(device,1,&AcquireFence,VK_TRUE,1000000000ULL),"acquire wait");
  // Native scanout owns a PRESENT -> color -> PRESENT transaction. Establish
  // its declared entry layout, with black letterboxing, for this image.
  VkImageMemoryBarrier b{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};b.oldLayout=Initialized[Index]?VK_IMAGE_LAYOUT_PRESENT_SRC_KHR:VK_IMAGE_LAYOUT_UNDEFINED;b.newLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
  b.srcQueueFamilyIndex=b.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;b.image=Image();b.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};b.dstAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;
  vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,0,nullptr,1,&b);
  VkClearColorValue black{};vkCmdClearColorImage(cmd,Image(),VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,&black,1,&b.subresourceRange);
  b.oldLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;b.newLayout=VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;b.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;b.dstAccessMask=0;
  vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,0,0,nullptr,0,nullptr,1,&b);
  Initialized[Index]=true;Acquired=true;Frame=frame;return true;
 }
 void Present(VkQueue queue){
  if(!Acquired){if(Device&&!AndroidLowerAvailable.load())Destroy();return;}
  // Initial private hardware probe serializes completion. No CPU readback or
  // screenshot copying is used; both displays share the same guest update.
  Check(vkQueueWaitIdle(queue),"render completion");
  VkPresentInfoKHR p{VK_STRUCTURE_TYPE_PRESENT_INFO_KHR};p.swapchainCount=1;p.pSwapchains=&Swapchain;p.pImageIndices=&Index;
  auto r=vkQueuePresentKHR(queue,&p);Acquired=false;
  if(r==VK_ERROR_OUT_OF_DATE_KHR){Destroy();return;}
  if(r==VK_SUBOPTIMAL_KHR){
   // Android compositor rotation may report SUBOPTIMAL indefinitely, even
   // though identity pre-transform is valid and the surface has not changed.
   VkSurfaceCapabilitiesKHR caps{};Check(vkGetPhysicalDeviceSurfaceCapabilitiesKHR(physicalDevice,Surface,&caps),"updated capabilities");
   if(caps.currentExtent.width!=Capabilities.currentExtent.width||caps.currentExtent.height!=Capabilities.currentExtent.height||
      caps.currentTransform!=Capabilities.currentTransform||caps.supportedTransforms!=Capabilities.supportedTransforms||
      caps.minImageCount!=Capabilities.minImageCount||caps.maxImageCount!=Capabilities.maxImageCount)Destroy();
   return;
  }Check(r,"present");
 }
};
template<class F>class AndroidOutputRestore {F Restore;public:explicit AndroidOutputRestore(F f):Restore(std::move(f)){}~AndroidOutputRestore(){Restore();}};
}
#endif
