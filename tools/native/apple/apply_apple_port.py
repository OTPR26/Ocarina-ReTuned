"""Adapt the pinned SDL/Vulkan host for Apple's mobile SDKs."""
from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from apply_macos_port import apply as apply_macos
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'reframed'))
from apply_native_port import edit

def apply(engine):
    engine=Path(engine)
    if "RETUNED_APPLE_MOBILE" not in (engine/"tools/oot3d/native_game_runtime/oot3d_native_game.cpp").read_text():
        apply_macos(engine)
    runtime=engine/'runtime/three_ds_recomp'
    cmake=runtime/'CMakeLists.txt'
    edit(cmake,'    enable_language(OBJCXX)','    enable_language(OBJC OBJCXX)')
    # CMake's built-in Apple toolchains select the SDK before project().
    edit(cmake,'    include(cmake/ios-toolchain-populate.cmake)','    # Apple mobile builds use the SDK selected by the top-level toolchain.')
    edit(cmake,'\tif(ANDROID)\n\t\tinclude(cmake/dependencies/android-vulkan.cmake)',
         '\tif((CMAKE_SYSTEM_NAME STREQUAL "iOS" OR CMAKE_SYSTEM_NAME STREQUAL "tvOS"))\n        include(cmake/dependencies/apple-vulkan.cmake)\n\telseif(ANDROID)\n\t\tinclude(cmake/dependencies/android-vulkan.cmake)')
    recipe=(runtime/'cmake/dependencies/android-vulkan.cmake').read_text()
    recipe=recipe.replace('find_library(Vulkan_LIBRARY vulkan REQUIRED)',
        'if(NOT EXISTS "${Vulkan_LIBRARY}")\n    message(FATAL_ERROR "Supply the matching iOS/tvOS MoltenVK library")\nendif()')
    (runtime/'cmake/dependencies/apple-vulkan.cmake').write_text(recipe)
    for p in [cmake, runtime/'src/CMakeLists.txt', runtime/'src/ship/CMakeLists.txt', runtime/'src/fast/CMakeLists.txt']:
        s=p.read_text()
        s=''.join(line if 'tvOS' in line else line.replace('CMAKE_SYSTEM_NAME STREQUAL "iOS"','(CMAKE_SYSTEM_NAME STREQUAL "iOS" OR CMAKE_SYSTEM_NAME STREQUAL "tvOS")') for line in s.splitlines(keepends=True))
        p.write_text(s)
    for relative in ('src/ship/audio/Audio.cpp','src/fast/backends/gfx_sdl2.cpp'):
        path=runtime/relative
        path.write_text(path.read_text().replace('#ifdef __APPLE__','#if defined(__APPLE__) && !defined(__IOS__)').replace('#if defined(__APPLE__)\n','#if defined(__APPLE__) && !defined(__IOS__)\n'))
    context=runtime/'src/ship/Context.cpp'
    text=context.read_text()
    for function, variable in [('std::string Context::GetAppBundlePath()', 'RETUNED_RESOURCE_DIRECTORY'), ('std::string Context::GetAppDirectoryPath(', 'RETUNED_DATA_DIRECTORY')]:
        start=text.index(function)
        end=text.index('#endif',text.index('#ifdef __IOS__',start))
        before=text[start:end]
        if variable not in before:
            before=before.replace('    const char* home = getenv("HOME");', '    if (const char* root = getenv("'+variable+'")) return root;\n    const char* home = getenv("HOME");')
            text=text[:start]+before+text[end:]
    context.write_text(text)
    edit(runtime/'src/fast/backends/gfx_sdl2.cpp',
         '    Uint32 flags = SDL_WINDOW_BORDERLESS | SDL_WINDOW_SHOWN;',
         '    Uint32 flags = SDL_WINDOW_BORDERLESS | SDL_WINDOW_SHOWN | SDL_WINDOW_ALLOW_HIGHDPI;')
    edit(runtime/'src/fast/backends/gfx_sdl2.cpp',
         'void GfxWindowBackendSDL2::SetDimensions(uint32_t width, uint32_t height, int32_t posX, int32_t posY) {\n#ifdef __ANDROID__',
         'void GfxWindowBackendSDL2::SetDimensions(uint32_t width, uint32_t height, int32_t posX, int32_t posY) {\n#if defined(__ANDROID__) || defined(__IOS__)')
    app=engine/'ports/apple'
    app.mkdir(parents=True,exist_ok=True)
    for name in ('app.cmake','apple_main.mm','patch_sdl_scenes.py','finalize_bundle.py','touch_controls.mm','touch_controls.h','touch_input.cpp','touch_input_api.h','texture_folder.mm'):
        (app/name).write_text(Path(__file__).with_name(name).read_text())
    from importlib.util import spec_from_file_location,module_from_spec
    artwork_spec=spec_from_file_location('retuned_touch_artwork',Path(__file__).parents[1]/'prepare_touch_artwork.py')
    artwork=module_from_spec(artwork_spec);artwork_spec.loader.exec_module(artwork)
    artwork.generate(app/'touch_dpad.h')
    import shutil
    for platform in ('ios','tvos'):
        shutil.copytree(Path(__file__).resolve().parents[3]/'resources/icons'/platform/'Assets.xcassets',app/'assets'/platform/'Assets.xcassets',dirs_exist_ok=True)
    root=engine/'CMakeLists.txt';text=root.read_text()
    marker='include("${CMAKE_CURRENT_SOURCE_DIR}/ports/apple/app.cmake")'
    if marker not in text:root.write_text(text+'\n'+marker+'\n')
    edit(runtime/'src/CMakeLists.txt',
         '    set_xcode_property(${PROJECT_NAME} PRODUCT_BUNDLE_IDENTIFIER ${BUNDLE_ID} All)',
         '    set_target_properties(${PROJECT_NAME} PROPERTIES XCODE_ATTRIBUTE_PRODUCT_BUNDLE_IDENTIFIER "${BUNDLE_ID}")')
    main=engine/'tools/oot3d/native_game_runtime/oot3d_native_game.cpp' 
    edit(main,'int main(int argc, char** argv) {',
         '#if defined(RETUNED_APPLE_MOBILE)\nint RetunedNativeMain(int argc, char** argv) {\n#else\nint main(int argc, char** argv) {\n#endif')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('engine',type=Path);apply(p.parse_args().engine)
