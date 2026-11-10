"""Generate typed forwarding exports from the Vulkan headers' registry."""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET


def generate(registry):
    root = ET.parse(registry).getroot()
    names = set()
    for feature in root.findall('feature'):
        if 'vulkan' in feature.get('api', '').split(',') and float(feature.get('number', '99')) <= 1.3:
            for require in feature.findall('require'):
                names.update(command.get('name') for command in require.findall('command'))
    names.add('vkCreateAndroidSurfaceKHR')
    for extension in root.findall('extensions/extension'):
        if extension.get('name') in ('VK_KHR_surface', 'VK_KHR_swapchain'):
            for require in extension.findall('require'):
                names.update(command.get('name') for command in require.findall('command'))
    lines = ['// Generated from the pinned Vulkan registry.', '#include "driver_loader.h"']
    for command in root.findall('commands/command'):
        if 'vulkan' not in command.get('api', 'vulkan').split(','):
            continue
        proto = command.find('proto')
        if proto is None:
            continue
        name = proto.findtext('name')
        if name not in names:
            continue
        params = [p for p in command.findall('param') if 'vulkan' in p.get('api', 'vulkan').split(',')]
        declaration = ''.join(proto.itertext())
        arguments = ', '.join(''.join(p.itertext()) for p in params) or 'void'
        values = ', '.join(p.findtext('name') for p in params)
        lines += [f'extern "C" VKAPI_ATTR {declaration} VKAPI_CALL ({arguments}) {{',
                  f'    static auto function = reinterpret_cast<PFN_{name}>(RetunedVulkanSymbol("{name}"));',
                  f'    return function({values});', '}']
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('registry', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.write_text(generate(args.registry))
