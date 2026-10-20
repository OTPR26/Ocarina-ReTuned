#!/usr/bin/env python3
"""Apply the small macOS source fixes against the pinned runtime."""
from pathlib import Path
import argparse
import subprocess

REVISION = '17218b0cfdb944645bb5cde5249f313dca7e53ce'


def apply(root):
    root = Path(root)
    actual = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != REVISION:
        raise ValueError('Runtime revision differs from the tested port baseline.')
    patches = [
        ('runtime/three_ds_recomp/src/fast/backends/gfx_metal_shader.cpp',
         '== SHADER_ID_PICA_TEXTURE_ENV', '== Fast::SHADER_ID_PICA_TEXTURE_ENV'),
        ('runtime/three_ds_recomp/src/fast/oot3d/pica_shader_instrumentation.cpp',
         '    std::from_chars(text.data(), text.data() + text.size(), parsed);',
         '    std::istringstream parser(text);\n    parser.imbue(std::locale::classic());\n    parser >> parsed;'),
    ]
    patches.extend([
        ('tools/oot3d/native_game_runtime/oot3d_savestate_panel.cpp',
         'std::chrono::clock_cast<std::chrono::system_clock>(time)',
         'std::chrono::time_point_cast<std::chrono::system_clock::duration>(std::chrono::file_clock::to_sys(time))'),
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
    for relative, before, after in patches:
        path = root / relative
        source = path.read_text()
        if source.count(after) == 1:
            continue
        if source.count(before) != 1:
            raise ValueError('macOS source fix context changed: ' + relative)
        path.write_text(source.replace(before, after))



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    apply(parser.parse_args().engine)
