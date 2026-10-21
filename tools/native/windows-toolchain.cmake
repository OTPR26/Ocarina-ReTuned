# Shared by the neutral Windows host and its locally compiled title modules.
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR AMD64)
set(_retuned_tools "${CMAKE_CURRENT_LIST_DIR}")
set(CMAKE_C_COMPILER "${_retuned_tools}/llvm/bin/x86_64-w64-mingw32-clang.exe")
set(CMAKE_CXX_COMPILER "${_retuned_tools}/llvm/bin/x86_64-w64-mingw32-clang++.exe")
set(CMAKE_RC_COMPILER "${_retuned_tools}/llvm/bin/llvm-windres.exe")
set(CMAKE_AR "${_retuned_tools}/llvm/bin/llvm-ar.exe")
set(CMAKE_RANLIB "${_retuned_tools}/llvm/bin/llvm-ranlib.exe")
set(CMAKE_MAKE_PROGRAM "${_retuned_tools}/ninja/ninja.exe" CACHE FILEPATH "Bundled Ninja")
set(CMAKE_CXX_SCAN_FOR_MODULES OFF)
# Dependencies configured through vcpkg must also map their own source roots;
# mapping only the top-level host leaves paths inside static SDL objects.
set(_retuned_path_maps "-ffile-prefix-map=\"${CMAKE_SOURCE_DIR}=retuned-source\" -ffile-prefix-map=\"${CMAKE_BINARY_DIR}=retuned-build\"")
set(CMAKE_C_FLAGS_INIT "-D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00 ${_retuned_path_maps}")
set(CMAKE_CXX_FLAGS_INIT "-D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00 ${_retuned_path_maps}")
set(CMAKE_EXE_LINKER_FLAGS_INIT "-static")
set(CMAKE_SHARED_LINKER_FLAGS_INIT "-static")
