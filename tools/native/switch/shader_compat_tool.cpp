// SPDX-License-Identifier: GPL-2.0-or-later
// Host-only bridge to the same exact arithmetic rewrite used by the Switch path.
#include "shader_compat.h"
#include <iostream>
#include <iterator>
int main() {
    try {
        std::string source((std::istreambuf_iterator<char>(std::cin)), {});
        if (source.size() > 1024 * 1024) throw std::runtime_error("shader exceeds source bound");
        RetunedSwitchShader::Rewrite(source);
        std::cout << source;
        return std::cout ? 0 : 1;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
