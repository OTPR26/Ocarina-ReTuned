#!/usr/bin/env python3
"""Apply the small macOS source fixes against the pinned runtime."""
from pathlib import Path
import argparse
import subprocess
from apply_common_port import apply as apply_common

REVISION = '17218b0cfdb944645bb5cde5249f313dca7e53ce'


def apply(root):
    root = Path(root)
    actual = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != REVISION:
        raise ValueError('Runtime revision differs from the tested port baseline.')
    apply_common(root)
    patches = [
        ('runtime/three_ds_recomp/src/fast/backends/gfx_metal_shader.cpp',
         '== SHADER_ID_PICA_TEXTURE_ENV', '== Fast::SHADER_ID_PICA_TEXTURE_ENV'),
    ]
    patches.extend([
        ('tools/oot3d/native_game_runtime/oot3d_native_direct_aot.cpp',
         '#elif defined(__linux__)', '#elif defined(__linux__) || defined(__APPLE__)'),
        ('tools/oot3d/native_game_runtime/oot3d_native_direct_aot.cpp',
         '#if defined(_WIN32) || defined(__linux__)',
         '#if defined(_WIN32) || defined(__linux__) || defined(__APPLE__)', 4),
        ('tools/oot3d/native_game_runtime/oot3d_native_direct_aot.cpp',
         '#include <dlfcn.h>', '#include <dlfcn.h>\n#if defined(__APPLE__)\n#include <mach-o/dyld.h>\n#endif'),
        ('tools/oot3d/native_game_runtime/oot3d_native_direct_aot.cpp',
         '#include <span>', '#include <span>\n#include <vector>'),
        ('tools/oot3d/native_game_runtime/oot3d_native_direct_aot.cpp',
         '''        path = std::filesystem::read_symlink("/proc/self/exe").parent_path() /
               "triaevum_title_aot.so";''',
         '''#if defined(__APPLE__)
        uint32_t size = 4096;
        std::vector<char> executable(size);
        if (_NSGetExecutablePath(executable.data(), &size) != 0) {
          executable.resize(size);
          if (_NSGetExecutablePath(executable.data(), &size) != 0) return nullptr;
        }
        path = std::filesystem::weakly_canonical(executable.data()).parent_path() /
               "triaevum_title_aot.dylib";
#else
        path = std::filesystem::read_symlink("/proc/self/exe").parent_path() /
               "triaevum_title_aot.so";
#endif'''),
        ('CMake/oot3d/game.cmake',
         '''        target_link_libraries(oot3d_native_game PRIVATE
            triaevum_title_aot_stub)''',
         '''        if(NOT APPLE)
            target_link_libraries(oot3d_native_game PRIVATE triaevum_title_aot_stub)
        endif()'''),
        ('CMake/oot3d/host_services.cmake',
         '''        target_link_libraries(oot3d_game_module PRIVATE
            triaevum_title_aot_stub)''',
         '''        if(NOT APPLE)
            target_link_libraries(oot3d_game_module PRIVATE triaevum_title_aot_stub)
        endif()'''),
        ('runtime/three_ds_recomp/src/fast/backends/gfx_vulkan_device.cpp',
         '    VkInstanceCreateInfo createInfo{ VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO };',
         '''    VkInstanceCreateInfo createInfo{ VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO };
#ifdef __APPLE__
    const bool portabilityAvailable = std::any_of(
        available.begin(), available.end(), [](const auto& extension) {
            return std::strcmp(extension.extensionName,
                               VK_KHR_PORTABILITY_ENUMERATION_EXTENSION_NAME) == 0;
        });
    if (portabilityAvailable) {
        if (std::none_of(extensions.begin(), extensions.end(), [](const char* name) {
                return std::strcmp(name, VK_KHR_PORTABILITY_ENUMERATION_EXTENSION_NAME) == 0;
            }))
            extensions.push_back(VK_KHR_PORTABILITY_ENUMERATION_EXTENSION_NAME);
        createInfo.flags |= VK_INSTANCE_CREATE_ENUMERATE_PORTABILITY_BIT_KHR;
    }
#endif'''),
        ('runtime/three_ds_recomp/src/fast/backends/gfx_vulkan_device.cpp',
         '    std::vector<const char*> extensions = { VK_KHR_SWAPCHAIN_EXTENSION_NAME };',
         '''    std::vector<const char*> extensions = { VK_KHR_SWAPCHAIN_EXTENSION_NAME };
#ifdef __APPLE__
    if (hasExtension("VK_KHR_portability_subset"))
        extensions.push_back("VK_KHR_portability_subset");
#endif'''),
    ])
    for relative, before, after, *counts in patches:
        expected = counts[0] if counts else 1
        path = root / relative
        source = path.read_text()
        if source.count(after) == expected:
            continue
        if source.count(before) != expected:
            raise ValueError('macOS source fix context changed: ' + relative)
        path.write_text(source.replace(before, after))



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    apply(parser.parse_args().engine)
