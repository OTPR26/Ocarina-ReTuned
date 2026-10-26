"""Keep heart-pair sampling away from neighboring atlas-cell borders."""
from pathlib import Path


def apply(root):
    path = Path(root) / 'src/native_hud.c'
    text = path.read_text()
    before = '''    float v1 = 1.0f - (512.5f + (float)row * 64.0f) / 1024.0f;
    float v0 = v1 - 63.0f / 1024.0f;'''
    after = '''    // Keep the vertical filter footprint inside the transparent gutter.
    // Half a source pixel can still expose the adjacent tile at HUD scale.
    float v1 = 1.0f - (514.0f + (float)row * 64.0f) / 1024.0f;
    float v0 = v1 - 60.0f / 1024.0f;'''
    if after in text:
        return
    if text.count(before) != 1:
        raise ValueError('Heart-pair atlas sampling context changed')
    path.write_text(text.replace(before, after))


if __name__ == '__main__':
    import sys
    apply(sys.argv[1])
