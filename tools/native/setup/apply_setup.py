"""Install the desktop-only first-run bootstrap before native title loading."""
from pathlib import Path
import re


def apply(engine):
    engine = Path(engine)
    source = Path(__file__).parent
    destination = engine / 'ports/retuned-setup'
    destination.mkdir(parents=True, exist_ok=True)
    for name in ('first_run.cpp', 'first_run.h', 'setup.cmake'):
        (destination / name).write_text((source / name).read_text())
    entry = engine / 'tools/oot3d/native_game_runtime/oot3d_native_game.cpp'
    text = entry.read_text()
    include = '#if defined(RETUNED_DESKTOP_SETUP)\n#include "first_run.h"\n#endif\n'
    if include not in text:
        text = include + text
    marker = 'int main(int argc, char** argv) {\n'
    addition = '''#if defined(RETUNED_DESKTOP_SETUP)
    std::filesystem::path setupProfile;
    if (!RetunedFirstRun(argc, argv, setupProfile)) return 0;
    const auto setupProfileBytes = setupProfile.u8string();
    std::string setupProfileText(setupProfileBytes.begin(), setupProfileBytes.end());
    char* setupArguments[] = {argv[0], const_cast<char*>("--launch-profile"), setupProfileText.data()};
    if (!setupProfile.empty()) { argc = 3; argv = setupArguments; }
#endif
'''
    start = text.index(marker)
    text = text[:start] + re.sub(r'#if defined\(RETUNED_DESKTOP_SETUP\)\n.*?#endif\n', '', text[start:], flags=re.DOTALL)
    start = text.index(marker)
    position = text.index('    try {\n', start) + len('    try {\n')
    text = text[:position] + addition + text[position:]
    entry.write_text(text)
    game = engine / 'CMake/oot3d/game.cmake'
    include = 'include("${CMAKE_CURRENT_SOURCE_DIR}/ports/retuned-setup/setup.cmake")'
    if include not in game.read_text():
        game.write_text(game.read_text() + '\n' + include + '\n')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    apply(parser.parse_args().engine)
