#define FMT_HEADER_ONLY
#include <fmt/format.h>
#include <cassert>
#include <string>
int main() {
    const char* file = "sample.cpp";
    int line = 42;
    const auto result = fmt::format(FMT_STRING("{} [{}({})]"), "sample error", file, line);
    assert(result == "sample error [sample.cpp(42)]");
    assert(fmt::format("value={}", 123) == "value=123");
    bool rejected = false;
    try { (void)fmt::format(fmt::runtime("{} {}"), 1); }
    catch (const fmt::format_error&) { rejected = true; }
    assert(rejected);
}
