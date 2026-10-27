cmake_minimum_required(VERSION 3.30)
project(OcarinaReTunedPrivateTitle LANGUAGES CXX)
if(NOT APPLE AND NOT ANDROID AND NOT WIN32 AND NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
    message(FATAL_ERROR "Unsupported private title platform")
endif()
if(ANDROID AND NOT CMAKE_ANDROID_ARCH_ABI STREQUAL "arm64-v8a")
    message(FATAL_ERROR "Android requires arm64-v8a")
endif()
if(APPLE AND NOT CMAKE_OSX_ARCHITECTURES STREQUAL "arm64")
    message(FATAL_ERROR "macOS requires an explicit arm64 architecture")
endif()
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_SCAN_FOR_MODULES OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
if(CMAKE_SYSTEM_NAME STREQUAL "Linux" AND NOT ANDROID)
    # The host and title exchange C++ memory objects, not just C ABI records.
    include(CheckCXXSourceCompiles)
    unset(RETUNED_LINUX_CXX_ABI_SUPPORTED CACHE)
    check_cxx_source_compiles([=[
        #include <string>
        #include <functional>
        #include <vector>
        #if !defined(__GLIBCXX__) || !defined(_GLIBCXX_USE_CXX11_ABI) || _GLIBCXX_USE_CXX11_ABI != 1
        #error The Linux host requires the libstdc++ C++11 ABI
        #endif
        #ifdef _GLIBCXX_DEBUG
        #error Debug containers are incompatible with the Linux host
        #endif
        static_assert(sizeof(void*) == 8);
        static_assert(sizeof(std::string) == 32);
        static_assert(sizeof(std::function<void()>) == 32);
        static_assert(sizeof(std::vector<unsigned char>) == 24);
        int main() { return 0; }
    ]=] RETUNED_LINUX_CXX_ABI_SUPPORTED)
    if(NOT RETUNED_LINUX_CXX_ABI_SUPPORTED)
        message(FATAL_ERROR
            "Linux preparation requires GCC or Clang with libstdc++ and its C++11 ABI. "
            "Zig's default libc++ is incompatible with this host. "
            "Use your distribution's g++ or clang++ with libstdc++ development headers.")
    endif()
endif()
option(RETUNED_CHECK_COMPILER_ONLY "Check the preparation compiler without game input" OFF)
if(RETUNED_CHECK_COMPILER_ONLY)
    return()
endif()
set(RETUNED_RUNTIME_SOURCE "" CACHE PATH "Pinned runtime source checkout")
set(TRIAEVUM_TRANSLATED_TITLE_DIR "" CACHE PATH "Private, verified generated title source")
if(NOT EXISTS "${RETUNED_RUNTIME_SOURCE}/tools/triaevum_release/cmake/TitleSupport.cmake")
    message(FATAL_ERROR "A pinned runtime source checkout is required")
endif()
include("${RETUNED_RUNTIME_SOURCE}/tools/triaevum_release/cmake/TranslatedTitleSources.cmake")
triaevum_translated_title_sources("${TRIAEVUM_TRANSLATED_TITLE_DIR}" sources)
set(RETUNED_JSON_INCLUDE_DIR "" CACHE PATH "Bundled neutral JSON headers")
if(RETUNED_JSON_INCLUDE_DIR)
    if(NOT EXISTS "${RETUNED_JSON_INCLUDE_DIR}/nlohmann/json.hpp")
        message(FATAL_ERROR "The preparation kit is missing its JSON headers")
    endif()
    add_library(retuned_json_headers INTERFACE)
    target_include_directories(retuned_json_headers INTERFACE "${RETUNED_JSON_INCLUDE_DIR}")
    add_library(nlohmann_json::nlohmann_json ALIAS retuned_json_headers)
else()
    find_package(nlohmann_json REQUIRED)
endif()
include("${RETUNED_RUNTIME_SOURCE}/tools/triaevum_release/cmake/TitleSupport.cmake")
triaevum_add_title_support("${RETUNED_RUNTIME_SOURCE}" "${RETUNED_RUNTIME_SOURCE}/tools/oot3d/native_a32_runtime/upstream")
add_library(retuned_private_title SHARED ${sources}
    "${RETUNED_RUNTIME_SOURCE}/tools/oot3d/native_game_runtime/triaevum_title_whole_aot_plugin.cpp")
target_include_directories(retuned_private_title PRIVATE "${TRIAEVUM_TRANSLATED_TITLE_DIR}")
target_compile_definitions(retuned_private_title PRIVATE OOT3D_NATIVE_GENERATED_WHOLE_AOT=1)
if(MSVC)
    target_compile_options(retuned_private_title PRIVATE /O1 /EHsc /fp:strict)
    target_compile_options(triaevum_title_whole_aot_support PRIVATE /O1 /fp:strict)
    target_compile_definitions(retuned_private_title PRIVATE NOMINMAX)
    set_property(TARGET retuned_private_title PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
else()
    target_compile_options(retuned_private_title PRIVATE -O1 -g0 -ffp-contract=off)
    target_compile_options(triaevum_title_whole_aot_support PRIVATE -O1 -g0 -ffp-contract=off)
endif()
target_link_libraries(retuned_private_title PRIVATE triaevum_title_whole_aot_support)
option(RETUNED_REPRODUCIBLE_PATHS "Remove local preparation paths from title modules" OFF)
if(RETUNED_REPRODUCIBLE_PATHS AND NOT MSVC)
    foreach(target retuned_private_title triaevum_title_whole_aot_support)
        # Target arguments retain spaces correctly; CMAKE_CXX_FLAGS is reparsed
        # by nested compiler checks and must not carry quoted private paths.
        target_compile_options(${target} PRIVATE
            "-ffile-prefix-map=${RETUNED_RUNTIME_SOURCE}=/runtime"
            "-ffile-prefix-map=${TRIAEVUM_TRANSLATED_TITLE_DIR}=/game"
            "-ffile-prefix-map=${PROJECT_SOURCE_DIR}=/retuned/title"
            "-ffile-prefix-map=${PROJECT_BINARY_DIR}=/build")
    endforeach()
endif()
set_target_properties(retuned_private_title PROPERTIES PREFIX "" OUTPUT_NAME "triaevum_title_aot"
    CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN ON)
if(ANDROID)
    target_link_options(retuned_private_title PRIVATE -Wl,--no-undefined -Wl,-z,max-page-size=16384)
endif()
