"""Crop lower-strip artwork from locally decoded game/selected-pack atlases.

Preparation helper for the optional dual-screen equipment panel. Inputs and outputs
contain the user's game/texture data and must never be committed or bundled
in a public host. No artwork is contained in this source file.
"""
from pathlib import Path
import argparse
import binascii
import hashlib
import json
import struct
import zlib


def _png(width, height, rgba):
    def chunk(kind, data):
        return (struct.pack('>I', len(data)) + kind + data +
                struct.pack('>I', binascii.crc32(kind + data) & 0xffffffff))
    rows = b''.join(b'\0' + rgba[y * width * 4:(y + 1) * width * 4]
                    for y in range(height))
    return (b'\x89PNG\r\n\x1a\n' +
            chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))


def prepare_romfs(romfs, output):
    """Create the panel's local PNG cache using only bundled standard-library tools."""
    from prepare_ui_assets import RomFs
    from ui_texture import decode, decode_compressed

    source = RomFs(romfs)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    images = {}
    sources = {}
    for name in ('menu_item_parts00', 'icon_item_menu00', 'menu_option_parts00'):
        data = source.read('menu/02_EU_ENGLISH/' + name + '.ctxb')
        try:
            width, height, rgba = decode(data)
        except ValueError:
            width, height, rgba = decode_compressed(data)
        expected = 512 if name == 'icon_item_menu00' else 256
        if width != expected or height != expected:
            raise ValueError('Unsupported equipment-panel atlas dimensions')
        images[name] = (width, rgba)
        sources[name] = hashlib.sha256(data).hexdigest()

    def crop(atlas, rect, name, rotate=False):
        stride, rgba = images[atlas]
        left, top, right, bottom = rect
        width, height = right - left, bottom - top
        if rotate:
            pixels = b''.join(rgba[((top + x) * stride + right - 1 - y) * 4:
                                  ((top + x) * stride + right - 1 - y) * 4 + 4]
                              for y in range(width) for x in range(height))
            width, height = height, width
        else:
            pixels = b''.join(rgba[((top + y) * stride + left) * 4:
                                  ((top + y) * stride + right) * 4]
                              for y in range(height))
        (output / (name + '.png')).write_bytes(_png(width, height, pixels))

    crop('menu_item_parts00', (140, 136, 192, 188), 'button')
    crop('menu_option_parts00', (0, 128, 120, 176), 'save')
    crop('menu_item_parts00', (198, 2, 254, 238), 'stone', rotate=True)
    for i in range(3):
        crop('icon_item_menu00', (336 + i * 42, 210, 378 + i * 42, 252), 'boots-' + str(i + 1))
        crop('icon_item_menu00', (210 + i * 42, 210, 252 + i * 42, 252), 'tunic-' + str(i + 1))
    crop('icon_item_menu00', (126, 378, 168, 420), 'agony')
    receipt = {'format': 'retuned_local_equipment_art_v1', 'private_local_artifact': True,
               'sources': sources, 'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                           for p in sorted(output.glob('*.png'))}}
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def prepare(background, menu, icons, output):
    from PIL import Image
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)

    def load(path, base, rectangular=False):
        path = Path(path)
        if not path.is_file() or path.stat().st_size > 64 * 1024**2:
            raise ValueError('Missing or oversized local UI atlas')
        image = Image.open(path)
        if (image.width != image.height * (2 if rectangular else 1) or
                image.width % base or image.width > 8192):
            raise ValueError('Unsupported local UI atlas dimensions')
        image.load()
        return image.convert('RGBA'), image.width / base

    def crop(image, scale, rect, name):
        image.crop(tuple(round(x * scale) for x in rect)).save(output / (name + '.png'))

    image, scale = load(background, 512, rectangular=True)
    # The native inside-page canvas uses the first 320x240 of this 512x256
    # atlas. Retain the extra sixteen rows for continuous footer sampling.
    leather = image.crop((0, 0, round(320*scale), round(256*scale)))
    leather.thumbnail((1280, 1024), Image.Resampling.LANCZOS)
    leather.save(output / 'leather.png')
    image, scale = load(menu, 256)
    crop(image, scale, (140, 136, 192, 188), 'button')
    # Existing gray stone behind the Items side buttons. Rotate the long
    # uninterrupted atlas column to span the footer without tiled seams.
    stone = image.crop(tuple(round(x*scale) for x in (198, 2, 254, 238)))
    stone = stone.transpose(Image.Transpose.ROTATE_90)
    stone.thumbnail((1536, 512), Image.Resampling.LANCZOS)
    stone.save(output / 'stone.png')
    image, scale = load(icons, 512)
    for i in range(3):
        crop(image, scale, (336 + i*42, 210, 378 + i*42, 252), 'boots-' + str(i+1))
        crop(image, scale, (210 + i*42, 210, 252 + i*42, 252), 'tunic-' + str(i+1))
    crop(image, scale, (126, 378, 168, 420), 'agony')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('background', 'menu', 'icons', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    prepare(args.background, args.menu, args.icons, args.output)
