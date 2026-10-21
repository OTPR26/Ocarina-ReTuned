#include <cassert>
#include <chrono>
#include <filesystem>
#include <string>
#include <iomanip>
#include <locale>
#include <sstream>

static float literal(float value) {
    std::ostringstream text;
    text.imbue(std::locale::classic());
    text << std::fixed << std::setprecision(6) << value;
    std::istringstream parser(text.str());
    parser.imbue(std::locale::classic());
    float parsed = 0;
    parser >> parsed;
    return parsed;
}

int main() {
    const auto file_time = std::filesystem::file_time_type::clock::now();
    const auto system_time = std::chrono::time_point_cast<std::chrono::system_clock::duration>(
        std::chrono::system_clock::now() + (file_time - std::filesystem::file_time_type::clock::now()));
    assert(std::chrono::abs(system_time - std::chrono::system_clock::now()) < std::chrono::seconds(5));
    const auto older = file_time - std::chrono::hours(24);
    const auto older_system = std::chrono::time_point_cast<std::chrono::system_clock::duration>(
        std::chrono::system_clock::now() + (older - std::filesystem::file_time_type::clock::now()));
    assert(std::chrono::abs((system_time - older_system) - std::chrono::hours(24)) < std::chrono::seconds(1));
    const auto stamp = std::to_string(std::chrono::duration_cast<std::chrono::nanoseconds>(file_time.time_since_epoch()).count());
    assert(!stamp.empty());
    assert(literal(0.0f) == 0.0f);
    assert(literal(0.5f) == 0.5f);
    assert(literal(1.0f) == 1.0f);
    assert(literal(0.1234567f) == 0.123457f);
    assert(literal(-0.002f) == -0.002f);
}
