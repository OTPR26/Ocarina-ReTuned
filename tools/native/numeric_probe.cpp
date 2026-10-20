#include <cassert>
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
    assert(literal(0.0f) == 0.0f);
    assert(literal(0.5f) == 0.5f);
    assert(literal(1.0f) == 1.0f);
    assert(literal(0.1234567f) == 0.123457f);
    assert(literal(-0.002f) == -0.002f);
}
