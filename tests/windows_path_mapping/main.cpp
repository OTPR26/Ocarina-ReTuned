// SPDX-License-Identifier: GPL-2.0-or-later
#include <cstdio>
#include <cstring>
extern "C" const char* source_path(void);
extern "C" const char* generated_path(void);

bool matches(const char* path, const char* expected) {
    while (*path && *expected) {
        const char actual = *path++;
        if ((actual == '\\' ? '/' : actual) != *expected++) return false;
    }
    return *path == *expected;
}

int main() {
    if (!matches(source_path(), "retuned-source/library.c") ||
        !matches(generated_path(), "retuned-build/generated.c") ||
        !matches(__FILE__, "retuned-source/main.cpp")) return 1;
    std::puts("Static C and C++ source/build paths are mapped.");
}
