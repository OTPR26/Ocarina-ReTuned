#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <dlfcn.h>

struct TitleProgram {
    uint32_t abi;
    uint32_t size;
    const uint32_t* entries;
    size_t entry_count;
    void* execute;
    void* active;
    void* observable_exit;
    uint32_t memory_visibility;
};
static_assert(sizeof(TitleProgram) == 56);
static_assert(offsetof(TitleProgram, memory_visibility) == 48);

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    void* library = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!library) { std::puts("Native title could not be loaded."); return 1; }
    using Query = const TitleProgram* (*)(uint32_t);
    const auto query = reinterpret_cast<Query>(dlsym(library, "triaevum_title_whole_aot_query"));
    const TitleProgram* program = query ? query(2) : nullptr;
    const bool valid = program && program->abi == 2 && program->size == sizeof(TitleProgram) &&
        program->memory_visibility == 3 && program->entry_count > 0 && program->entries &&
        program->execute && program->active && program->observable_exit && !query(1);
    if (valid) std::puts("Native title ABI 2 and memory visibility 3 verified; incompatible ABI rejected.");
    dlclose(library);
    return valid ? 0 : 1;
}
