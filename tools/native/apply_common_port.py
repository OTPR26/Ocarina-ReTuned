#!/usr/bin/env python3
"""Apply standard-library compatibility fixes shared by ARM64 targets."""
from pathlib import Path


def apply(root):
    patches = [
        ('runtime/three_ds_recomp/src/fast/oot3d/pica_shader_instrumentation.cpp',
         '    std::from_chars(text.data(), text.data() + text.size(), parsed);',
         '    std::istringstream parser(text);\n    parser.imbue(std::locale::classic());\n    parser >> parsed;'),
        ('tools/oot3d/native_game_runtime/oot3d_scene_environment.cpp',
         'std::to_string(error ? 0 : time.time_since_epoch().count())',
         'std::to_string(error ? 0LL : std::chrono::duration_cast<std::chrono::nanoseconds>(time.time_since_epoch()).count())'),
        ('tools/oot3d/native_game_runtime/oot3d_savestate_panel.cpp',
         'std::chrono::clock_cast<std::chrono::system_clock>(time)',
         'std::chrono::time_point_cast<std::chrono::system_clock::duration>(std::chrono::file_clock::to_sys(time))'),
    ]
    for relative, before, after in patches:
        path = Path(root) / relative
        source = path.read_text()
        if source.count(after) == 1:
            continue
        if source.count(before) != 1:
            raise ValueError('Portable source fix context changed: ' + relative)
        path.write_text(source.replace(before, after))
