include(FetchContent)
FetchContent_Declare(retuned_adrenotools
    GIT_REPOSITORY https://github.com/bylaws/libadrenotools.git
    GIT_TAG 8fae8ce254dfc1344527e05301e43f37dea2df80
    GIT_SUBMODULES lib/linkernsbypass
    GIT_SUBMODULES_RECURSE TRUE)
set(_retuned_shared "${BUILD_SHARED_LIBS}")
set(BUILD_SHARED_LIBS OFF)
FetchContent_MakeAvailable(retuned_adrenotools)
set(BUILD_SHARED_LIBS "${_retuned_shared}")
foreach(target adrenotools linkernsbypass)
    set_target_properties(${target} PROPERTIES POSITION_INDEPENDENT_CODE ON)
    target_compile_options(${target} PRIVATE -fvisibility=hidden)
endforeach()
find_package(Python3 REQUIRED COMPONENTS Interpreter)
execute_process(COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_LIST_DIR}/generate_vulkan_forwarders.py"
    "${android_vulkan_headers_SOURCE_DIR}/registry/vk.xml"
    "${CMAKE_CURRENT_BINARY_DIR}/retuned_vulkan_forwarders.cpp"
    COMMAND_ERROR_IS_FATAL ANY)
add_library(retuned_vulkan SHARED "${CMAKE_CURRENT_LIST_DIR}/driver_loader.cpp"
    "${CMAKE_CURRENT_BINARY_DIR}/retuned_vulkan_forwarders.cpp")
target_include_directories(retuned_vulkan PRIVATE "${CMAKE_CURRENT_LIST_DIR}" PUBLIC "${Vulkan_INCLUDE_DIR}")
target_link_libraries(retuned_vulkan PRIVATE log dl)
add_library(retuned_driver SHARED "${CMAKE_CURRENT_LIST_DIR}/driver_custom.cpp")
target_link_libraries(retuned_driver PRIVATE adrenotools)
target_link_options(retuned_driver PRIVATE -Wl,--exclude-libs,ALL)
foreach(target retuned_vulkan retuned_driver hook_impl main_hook file_redirect_hook gsl_alloc_hook)
    target_link_options(${target} PRIVATE -Wl,-z,max-page-size=16384)
    set_target_properties(${target} PROPERTIES LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/product")
endforeach()
add_dependencies(retuned_vulkan retuned_driver main_hook hook_impl)
add_library(Vulkan::Vulkan ALIAS retuned_vulkan)
