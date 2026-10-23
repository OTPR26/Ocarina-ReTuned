if(CMAKE_SYSTEM_NAME STREQUAL "iOS" OR CMAKE_SYSTEM_NAME STREQUAL "tvOS")
    enable_language(OBJC OBJCXX)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    execute_process(COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_LIST_DIR}/patch_sdl_scenes.py" "${SDL2_SOURCE_DIR}" COMMAND_ERROR_IS_FATAL ANY)
    target_sources(oot3d_native_game PRIVATE "${CMAKE_CURRENT_LIST_DIR}/apple_main.mm" "${CMAKE_CURRENT_LIST_DIR}/startup_status.mm")
    if(CMAKE_SYSTEM_NAME STREQUAL "tvOS")
        target_sources(oot3d_native_game PRIVATE "${CMAKE_CURRENT_LIST_DIR}/television_remote.mm")
        set_source_files_properties("${CMAKE_CURRENT_LIST_DIR}/television_remote.mm" PROPERTIES COMPILE_FLAGS "-fobjc-arc")
    endif()
    if(CMAKE_SYSTEM_NAME STREQUAL "iOS")
        target_sources(oot3d_native_game PRIVATE "${CMAKE_CURRENT_LIST_DIR}/touch_controls.mm" "${CMAKE_CURRENT_LIST_DIR}/touch_input.cpp" "${CMAKE_CURRENT_LIST_DIR}/texture_folder.mm")
        target_link_libraries(oot3d_native_game PRIVATE "-framework UniformTypeIdentifiers")
        set_source_files_properties("${CMAKE_CURRENT_LIST_DIR}/texture_folder.mm" "${CMAKE_CURRENT_LIST_DIR}/touch_controls.mm" PROPERTIES COMPILE_FLAGS "-fobjc-arc")
    endif()
    target_compile_definitions(oot3d_native_game PRIVATE RETUNED_APPLE_MOBILE=1 __IOS__)
    set_source_files_properties("${CMAKE_CURRENT_LIST_DIR}/apple_main.mm" "${CMAKE_CURRENT_LIST_DIR}/startup_status.mm" PROPERTIES COMPILE_FLAGS "-fobjc-arc")
    target_link_libraries(oot3d_native_game PRIVATE SDL2::SDL2main "-framework UIKit" "-framework GameController")
    set_target_properties(oot3d_native_game PROPERTIES
        MACOSX_BUNDLE TRUE OUTPUT_NAME OcarinaReTuned
        MACOSX_BUNDLE_GUI_IDENTIFIER io.github.otpr26.ocarinaretuned
        MACOSX_BUNDLE_BUNDLE_NAME "Ocarina ReTuned"
        MACOSX_BUNDLE_SHORT_VERSION_STRING "0.1.1"
        MACOSX_BUNDLE_BUNDLE_VERSION "2"
        BUILD_RPATH "@executable_path/Frameworks"
        INSTALL_RPATH "@executable_path/Frameworks")
endif()

if(CMAKE_SYSTEM_NAME STREQUAL "iOS" OR CMAKE_SYSTEM_NAME STREQUAL "tvOS")
    set(nri_loader "${CMAKE_BINARY_DIR}/_deps/nri-src/Source/Shared/SharedExternal.h")
    if(EXISTS "${nri_loader}")
        file(READ "${nri_loader}" loader_source)
        string(REPLACE "\"libvulkan.1.dylib\"" "\"@executable_path/Frameworks/MoltenVK.framework/MoltenVK\"" loader_source "${loader_source}")
        file(WRITE "${nri_loader}" "${loader_source}")
    endif()
endif()

if(CMAKE_SYSTEM_NAME STREQUAL "iOS" OR CMAKE_SYSTEM_NAME STREQUAL "tvOS")
    if(CMAKE_SYSTEM_NAME STREQUAL "tvOS")
        set(retuned_icon_platform tvos)
        set(retuned_icon_sdk appletvos)
        set(retuned_icon_device tv)
        set(retuned_icon_name AppIconTV)
    else()
        set(retuned_icon_platform ios)
        set(retuned_icon_sdk iphoneos)
        set(retuned_icon_device iphone)
        set(retuned_icon_name AppIcon)
    endif()
    add_custom_command(TARGET oot3d_native_game POST_BUILD
        COMMAND xcrun --sdk ${retuned_icon_sdk} actool
            "${CMAKE_CURRENT_LIST_DIR}/assets/${retuned_icon_platform}/Assets.xcassets"
            --compile "$<TARGET_BUNDLE_DIR:oot3d_native_game>"
            --platform ${retuned_icon_sdk} --target-device ${retuned_icon_device}
            --minimum-deployment-target 17.0 --app-icon ${retuned_icon_name}
            --output-partial-info-plist "${CMAKE_BINARY_DIR}/retuned-icons.plist"
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_LIST_DIR}/finalize_bundle.py"
            "$<TARGET_BUNDLE_DIR:oot3d_native_game>" ${retuned_icon_platform} "${CMAKE_BINARY_DIR}/retuned-icons.plist"
        VERBATIM)
endif()
