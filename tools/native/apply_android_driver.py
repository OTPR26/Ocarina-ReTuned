"""Route every Android Vulkan consumer through the selected process-owned loader."""
from pathlib import Path
import shutil


def edit(path, before, after):
    value = path.read_text()
    if after in value:
        return
    if value.count(before) != 1:
        raise ValueError('Android driver integration context changed: ' + path.name)
    path.write_text(value.replace(before, after))


def apply(engine):
    runtime = Path(engine) / 'runtime/three_ds_recomp'
    source = Path(__file__).parent / 'android'
    destination = runtime / 'cmake/dependencies/retuned-driver'
    destination.mkdir(parents=True, exist_ok=True)
    for name in ('graphics-driver.cmake', 'generate_vulkan_forwarders.py', 'driver_loader.h', 'driver_loader.cpp', 'driver_custom.cpp'):
        shutil.copy2(source / name, destination / name)
    edit(runtime / 'cmake/dependencies/android-vulkan.cmake',
         'find_library(Vulkan_LIBRARY vulkan REQUIRED)',
         'find_library(Vulkan_LIBRARY vulkan REQUIRED)\ninclude("${CMAKE_CURRENT_LIST_DIR}/retuned-driver/graphics-driver.cmake")')
    path = runtime / 'src/fast/oot3d/nri_interop_context.cpp'
    edit(path, '  nri::DeviceCreationVKDesc desc{};',
         '  nri::DeviceCreationVKDesc desc{};\n#ifdef __ANDROID__\n  desc.libraryPath = std::getenv("SDL_VULKAN_LIBRARY");\n#endif')
    value = path.read_text()
    if '#include <cstdlib>' not in value:
        path.write_text('#include <cstdlib>\n' + value)
