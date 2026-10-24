# The caller supplies a private, user-prepared title archive. It must never be
# included in a public host/toolkit archive.
set(CMAKE_DL_LIBS "")
if(RETUNED_REPRODUCIBLE_PATHS)
    # Compiler options are individual CMake arguments, including source paths
    # with spaces. The executable and neutral link inputs must not embed them.
    foreach(mapping "$ENV{HOME}=/user" "${CMAKE_BINARY_DIR}=/build"
                    "${FETCHCONTENT_BASE_DIR}=/deps" "${CMAKE_SOURCE_DIR}=/engine"
                    "${CMAKE_CURRENT_LIST_DIR}=/switch")
        add_compile_options("-ffile-prefix-map=${mapping}" "-fmacro-prefix-map=${mapping}")
    endforeach()
endif()
function(retuned_link_switch_title)
    if(NOT CMAKE_SYSTEM_NAME STREQUAL "NintendoSwitch")
        message(FATAL_ERROR "Switch title integration requires NintendoSwitch")
    endif()
    if(NOT EXISTS "${RETUNED_SWITCH_TITLE_ARCHIVE}")
        message(FATAL_ERROR "The locally prepared Switch title archive is missing")
    endif()
    target_link_options(oot3d_native_game PRIVATE "-Wl,--eh-frame-hdr" "-Wl,--wrap=_Unwind_Find_FDE" "-Wl,--wrap=exit" "-Wl,--wrap=main" "-Wl,--wrap=abort" "-Wl,--wrap=__cxa_throw")
    target_sources(oot3d_native_game PRIVATE "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/startup.cpp" "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/unwind.cpp")
    target_link_libraries(oot3d_native_game PRIVATE
        "-Wl,--whole-archive" "${RETUNED_SWITCH_TITLE_ARCHIVE}" "-Wl,--no-whole-archive")
endfunction()
cmake_language(DEFER CALL retuned_link_switch_title)
