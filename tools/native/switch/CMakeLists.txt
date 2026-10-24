cmake_minimum_required(VERSION 3.26)
project(ReTunedSwitchTitle LANGUAGES CXX)
if(NOT CMAKE_SYSTEM_NAME STREQUAL "NintendoSwitch")
    message(FATAL_ERROR "Use devkitPro's Switch toolchain")
endif()
foreach(required RETUNED_ENGINE RETUNED_GENERATED)
    if(NOT IS_DIRECTORY "${${required}}")
        message(FATAL_ERROR "${required} must name a local preparation directory")
    endif()
endforeach()
set(host "${RETUNED_ENGINE}/tools/oot3d/native_game_runtime")
set(a32 "${RETUNED_ENGINE}/tools/oot3d/native_a32_runtime")
file(GLOB shards CONFIGURE_DEPENDS "${RETUNED_GENERATED}/oot3d_whole_aot_shard_*.cpp")
if(NOT shards OR NOT EXISTS "${RETUNED_GENERATED}/oot3d_whole_aot_generated.cpp")
    message(FATAL_ERROR "Locally generated title sources are missing")
endif()
# This archive contains user-generated title code. Never publish it.
add_library(retuned_switch_title STATIC
    "${RETUNED_GENERATED}/oot3d_whole_aot_generated.cpp"
    ${shards}
    "${host}/triaevum_title_whole_aot_plugin.cpp")
target_compile_features(retuned_switch_title PRIVATE cxx_std_20)
target_compile_options(retuned_switch_title PRIVATE
    -O1 -g0 -fno-fast-math -ffp-contract=off -fno-rtti)
target_compile_definitions(retuned_switch_title PRIVATE OOT3D_NATIVE_GENERATED_WHOLE_AOT=1)
target_include_directories(retuned_switch_title PRIVATE
    "${RETUNED_GENERATED}" "${host}" "${a32}" "${a32}/upstream"
    "${a32}/upstream/recomp" "${a32}/mass_cpp" "${RETUNED_JSON_INCLUDE}")
# A shared-library build hides these entry points. A statically linked Switch
# build must give the title side distinct names from the host's ABI bridge.
set_source_files_properties(
    "${RETUNED_GENERATED}/oot3d_whole_aot_generated.cpp"
    "${host}/triaevum_title_whole_aot_plugin.cpp"
    PROPERTIES COMPILE_DEFINITIONS
    "Oot3dWholeAotEntryPoints=RetunedSwitchTitleEntryPoints;ExecuteOot3dWholeAotFunction=ExecuteRetunedSwitchTitleFunction")
