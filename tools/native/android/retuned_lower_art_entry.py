"""Add missing sidebar artwork from an existing prepared game, without recompilation."""
from pathlib import Path
import sys


def ensure_save(kit_path, installation):
    root = Path(installation)
    target = root / 'lower-equipment/save.png'
    if target.is_file() and not target.is_symlink():
        return str(target)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(kit_path) / 'project/tools/native'))
    from prepare_ui_assets import RomFs
    from ui_texture import decode, decode_compressed
    from prepare_lower_equipment_art import _png
    data = RomFs(root / 'romfs.bin').read('menu/02_EU_ENGLISH/menu_option_parts00.ctxb')
    try:
        width, height, rgba = decode(data)
    except ValueError:
        width, height, rgba = decode_compressed(data)
    if (width, height) != (256, 256):
        raise ValueError('Unsupported native Save artwork dimensions')
    pixels = b''.join(rgba[(y*width)*4:(y*width+120)*4] for y in range(128,176))
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.png.pending')
    try:
        temporary.write_bytes(_png(120, 48, pixels))
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return str(target)


def ensure_shields(kit_path, installation):
    """Backfill new panel icons without rebuilding the prepared title."""
    root = Path(installation)
    directory = root / 'lower-equipment'
    targets = [directory / f'shield-{i + 1}.png' for i in range(3)]
    if all(p.is_file() and not p.is_symlink() for p in targets):
        return str(directory)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(kit_path) / 'project/tools/native'))
    from prepare_ui_assets import RomFs
    from ui_texture import decode, decode_compressed
    from prepare_lower_equipment_art import _png
    data = RomFs(root / 'romfs.bin').read('menu/02_EU_ENGLISH/icon_item_menu00.ctxb')
    try:
        width, height, rgba = decode(data)
    except ValueError:
        width, height, rgba = decode_compressed(data)
    if (width, height) != (512, 512):
        raise ValueError('Unsupported shield artwork dimensions')
    directory.mkdir(parents=True, exist_ok=True)
    for i, target in enumerate(targets):
        if target.is_file() and not target.is_symlink():
            continue
        left = 84 + i * 42
        pixels = b''.join(rgba[(y*width+left)*4:(y*width+left+42)*4]
                          for y in range(210, 252))
        temporary = target.with_suffix('.png.pending')
        try:
            temporary.write_bytes(_png(42, 42, pixels))
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return str(directory)
