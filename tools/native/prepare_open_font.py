#!/usr/bin/env python3
"""Build OFL-licensed ReTuned Dialogue coverage and pair it with local game data.

The public QBF contains OFL typeface glyphs and an original diamond marker.
Runtime pairing needs no Pillow and leaves the native font's layout authoritative.
The paired ZIP contains native game data and is private installation output.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import zipfile
import tempfile

MAX_BYTES = 32 * 1024 * 1024
CODES = (*range(0x20, 0x7f), *range(0xa0, 0x100), 0x152, 0x153, 0x178, 0x2014, 0x201c, 0x201e, 0x20ac, 0x25c6)
# The long bold t crossbar crowds following stems on QBF's integer layout grid.
# Add trailing clearance without shifting or deforming its rasterized outline.
RIGHT_BEARING_ADJUSTMENTS = {ord('t'): 1}


def parse(data):
    if not 16 <= len(data) <= MAX_BYTES or data[:4] != b'QBF1':
        raise ValueError('Invalid QBF header')
    count, glyphs, fallback = struct.unpack_from('<HHH', data, 4)
    bpp, width, height, encoding = data[12:16]
    offset = 16 + count * 8
    if (bpp != 4 or encoding != 2 or not width or not height or width % 8 or height % 8 or
            not count or not glyphs or offset + glyphs * width * height // 2 != len(data)):
        raise ValueError('Invalid QBF coverage size')
    records = []
    previous = -1
    for index in range(count):
        at = 16 + index * 8
        code, glyph = struct.unpack_from('<HH', data, at)
        if code <= previous or glyph >= glyphs:
            raise ValueError('Invalid QBF directory')
        records.append((code, glyph, data[at + 4:at + 8]))
        previous = code
    if fallback not in {r[0] for r in records}:
        raise ValueError('Missing fallback character')
    return records, glyphs, fallback, width, height, offset


def build(typeface, output):
    # Build-time dependency only. No rasterizer/tool installation on user devices.
    from PIL import Image, ImageDraw, ImageFont
    face = ImageFont.truetype(str(typeface), 54)
    glyphs, records = [], []
    for index, code in enumerate(CODES):
        image = Image.new('L', (64, 64))
        if code == 0x25c6:
            # Liberation Sans lacks this UI marker; draw an original geometric diamond.
            ImageDraw.Draw(image).polygon([(32, 12), (52, 32), (32, 52), (12, 32)], fill=255)
        elif not chr(code).isspace():
            draw = ImageDraw.Draw(image)
            box = draw.textbbox((0, 0), chr(code), font=face, anchor='ls')
            width = box[2] - box[0]
            # Common baseline; no per-character vertical stretching.
            draw.text((32 - width / 2 - box[0], 52), chr(code), font=face, fill=255, anchor='ls')
        alpha = list(image.tobytes())
        glyphs.append(bytes((((alpha[i] + 8) // 17) << 4) | ((alpha[i + 1] + 8) // 17)
                            for i in range(0, len(alpha), 2)))
        advance = min(31, max(1, round(face.getlength(chr(code)) / 4)))
        records.append(struct.pack('<HH4B', code, index, 0, advance, 0, 0))
    data = b'QBF1' + struct.pack('<HHHH4B', len(CODES), len(CODES), 42, 0, 4, 64, 64, 2)
    data += b''.join(records) + b''.join(glyphs)
    parse(data)
    output = Path(output)
    if output.exists():
        raise ValueError('Refusing to overwrite font output')
    output.write_bytes(data)
    return {'name': 'ReTuned Dialogue', 'license': 'OFL-1.1',
            'source_sha256': hashlib.sha256(Path(typeface).read_bytes()).hexdigest(),
            'sha256': hashlib.sha256(data).hexdigest(), 'glyphs': len(CODES), 'cell': [64, 64]}


def build_matched(typeface, native_output, coverage_output, *, engine_tracking=1,
                  coverage_size=128):
    """Render a native/HD pair with the typeface's own advances and bearings.

    QBF advances are integer logical pixels (four coverage pixels). The game
    subtracts metric zero from the pen before drawing the cell. A fixed two
    pixel cell bearing therefore cancels the eight pixel raster origin. Keep
    the typeface's side bearings, baseline and proportions intact; never fit
    individual glyphs to a different font's metrics. Dialogue adds one logical
    pixel of tracking separately; exclude that from the stored advance so the
    final pen increment matches the typeface rather than adding extra tracking.
    """
    from PIL import Image, ImageDraw, ImageFont
    if not isinstance(engine_tracking, int) or not 0 <= engine_tracking <= 2:
        raise ValueError('Unsupported engine tracking')
    if coverage_size not in (64, 128):
        raise ValueError('Unsupported coverage cell size')
    scale = coverage_size / 64
    unit = coverage_size / 16
    face = ImageFont.truetype(str(typeface), round(54 * scale))
    # Layout must not change when selecting a denser atlas. Measure once at a
    # fixed design size, avoiding small raster-size rounding around half units.
    metric_face = ImageFont.truetype(str(typeface), 864)
    directory, images = [], []
    for index, code in enumerate(CODES):
        image = Image.new('L', (coverage_size, coverage_size))
        if code == 0x25c6:
            ImageDraw.Draw(image).polygon([(round(x*scale), round(y*scale))
                for x,y in ((28,12),(48,32),(28,52),(8,32))], fill=255)
            advance = 12 - engine_tracking
        else:
            natural_advance = metric_face.getlength(chr(code)) / 64
            advance = max(1, round(natural_advance) - engine_tracking)
            # QBF has integer advances. Divide the rounding remainder between
            # both side bearings instead of leaving all of it after the glyph.
            # This is optical centering, not pair kerning or glyph stretching.
            rounding = (advance + engine_tracking - natural_advance) * unit / 2
            ImageDraw.Draw(image).text((8*scale + rounding, 52*scale), chr(code),
                                      font=face, fill=255, anchor='ls')
            advance += RIGHT_BEARING_ADJUSTMENTS.get(code, 0)
        if not 1 <= advance <= 31:
            raise ValueError('Typeface advance exceeds QBF metric range')
        # Detect clipping rather than silently shrinking wide or accented glyphs.
        if image.getbbox() and (image.crop((0, 0, 1, coverage_size)).getbbox() or
                               image.crop((coverage_size-1, 0, coverage_size, coverage_size)).getbbox()):
            raise ValueError(f'Typeface exceeds cell bounds at U+{code:04X}')
        directory.append(struct.pack('<HH4B', code, index, 2, advance, 0, 0))
        images.append(image)
    outputs = [Path(native_output), Path(coverage_output)]
    if outputs[0].resolve() == outputs[1].resolve() or any(p.exists() or p.is_symlink() for p in outputs):
        raise ValueError('Matched font outputs must be distinct new files')
    hashes = {}
    for path, size in zip(outputs, (32, coverage_size)):
        payloads = []
        for image in images:
            if size != coverage_size:
                image = image.resize((size, size), Image.Resampling.LANCZOS)
            alpha = image.tobytes()
            payloads.append(bytes((((alpha[i] + 8) // 17) << 4) | ((alpha[i+1] + 8) // 17)
                                  for i in range(0, len(alpha), 2)))
        data = (b'QBF1' + struct.pack('<HHHH4B', len(CODES), len(CODES), 42, 0, 4, size, size, 2)
                + b''.join(directory) + b''.join(payloads))
        parse(data)
        with path.open('xb') as stream:
            stream.write(data)
        hashes[str(size)] = hashlib.sha256(data).hexdigest()
    return {'name': 'ReTuned Dialogue', 'license': 'OFL-1.1',
            'layout': 'typeface-advances-and-side-bearings',
            'engine_tracking': engine_tracking,
            'coverage_cell': coverage_size,
            'quantized_advance_alignment': 'balanced-side-bearings',
            'right_bearing_adjustments': {chr(k): v for k,v in RIGHT_BEARING_ADJUSTMENTS.items()},
            'source_sha256': hashlib.sha256(Path(typeface).read_bytes()).hexdigest(),
            'sha256': hashes, 'glyphs': len(CODES)}


def fit_glyph(native, native_width, native_height, coverage, width, height, metrics):
    """Fit licensed coverage to the local ROM's cell geometry, without copying artwork."""
    def unpack(data):
        return [v for n in data for v in ((n >> 4) * 17, (n & 15) * 17)]
    def bounds(alpha, w):
        points = [(i % w, i // w) for i, value in enumerate(alpha) if value]
        if not points:
            return None
        return min(x for x,y in points), min(y for x,y in points), max(x for x,y in points)+1, max(y for x,y in points)+1
    source, original = unpack(coverage), unpack(native)
    a, b = bounds(source, width), bounds(original, native_width)
    if not a or not b:
        return bytes(width * height // 2)
    # Native metrics describe the horizontal pen bearing and character width.
    # Keep the typeface's baseline and every vertical coordinate untouched:
    # bottom-aligning individual ink boxes turns apostrophes into commas.
    unit = width / 16
    left = max(0, round(metrics[0] * unit - 1))
    # Fill the stored advance with a consistent one-logical-pixel gutter.
    # Capping at the typeface's original ink width leaves variable empty space
    # (notably o versus n) even though the game keeps using the native advances.
    target_width = max(1, round(metrics[1]*unit-unit))
    target_width = min(target_width, width-left)
    if target_width < 1:
        raise ValueError('Native glyph metrics exceed the cell')
    top = a[1]
    target_height = a[3]-a[1]
    result = [0] * (width * height)
    # Bilinear sampling preserves anti-aliased coverage when adapting cell proportions.
    for y in range(target_height):
        sy = a[1] + (y+.5)*(a[3]-a[1])/target_height-.5
        y0 = max(a[1], min(a[3]-1, int(sy))); y1 = min(a[3]-1,y0+1); fy = max(0.,sy-y0)
        for x in range(target_width):
            sx = a[0] + (x+.5)*(a[2]-a[0])/target_width-.5
            x0 = max(a[0],min(a[2]-1,int(sx))); x1 = min(a[2]-1,x0+1); fx = max(0.,sx-x0)
            v = (1-fy)*((1-fx)*source[y0*width+x0]+fx*source[y0*width+x1]) + fy*((1-fx)*source[y1*width+x0]+fx*source[y1*width+x1])
            result[(top+y)*width+left+x] = min(15, max(0, round(v/17)))
    return bytes((result[i]<<4)|result[i+1] for i in range(0,len(result),2))


def pair(native, coverage, output, license_path, *, fit_native=False):
    """Map our independently rendered glyphs onto local native metrics/aliases."""
    records, glyphs, fallback, width, height, offset = parse(native)
    hd_records, _, _, hd_width, hd_height, hd_offset = parse(coverage)
    if hd_width % width or hd_height % height or hd_width // width != hd_height // height or hd_width < width:
        raise ValueError('Unsupported font coverage density')
    by_code = {r[0]: r[1] for r in hd_records}
    stride = hd_width * hd_height // 2
    alias = {}
    mappings = []
    for code, glyph, metrics in records:
        if code not in by_code:
            raise ValueError(f'Font lacks character U+{code:04X}')
        # Native aliases must resolve consistently even if Unicode has two labels.
        selected = alias.setdefault(glyph, by_code[code])
        mappings.append({'code': code, 'native_glyph': glyph, 'coverage_glyph': glyph,
                         'native_metrics_hex': metrics.hex()})
    directory = b''.join(struct.pack('<HH', code, glyph) + metrics for code, glyph, metrics in records)
    metrics_by_glyph = {glyph: metrics for code, glyph, metrics in records}
    payloads = []
    native_stride = width * height // 2
    for i in range(glyphs):
        selected = alias.get(i, by_code[fallback])
        pixels = coverage[hd_offset + selected * stride:hd_offset + (selected + 1) * stride]
        if fit_native and i in metrics_by_glyph:
            pixels = fit_glyph(native[offset+i*native_stride:offset+(i+1)*native_stride],
                width, height, pixels, hd_width, hd_height, metrics_by_glyph[i])
        payloads.append(pixels)
    payload = b''.join(payloads)
    hd = native[:13] + bytes([hd_width, hd_height]) + native[15:16] + directory + payload
    parse(hd)
    native_hash, hd_hash = hashlib.sha256(native).hexdigest(), hashlib.sha256(hd).hexdigest()
    native_name, hd_name = f'native/{native_hash}.qbf', f'coverage/{hd_hash}.qbf'
    manifest = {'format': 'oot3d_qbf_coverage_v1', 'runtime_enabled': True, 'minimum_output_height': 480,
        'name': 'ReTuned Dialogue', 'attribution': 'Based on Liberation Sans; Google Corporation and Red Hat, Inc.',
        'license': 'OFL-1.1', 'native_cell_fit': fit_native, 'fonts': [{'romfs_path': 'message/eu/ltn16.qbf',
        'native_file': native_name, 'coverage_file': hd_name, 'native_sha256': native_hash,
        'coverage_sha256': hd_hash, 'logical_cell': [width, height], 'coverage_cell': [hd_width, hd_height],
        'density': hd_width // width, 'fallback_code': fallback, 'characters': mappings,
        'replacement_metric_differences': 0}]}
    output = Path(output)
    temporary = output.with_name(output.name + '.partial')
    if output.exists() or output.is_symlink():
        raise ValueError('Refusing to overwrite coverage pack')
    created = False
    try:
        with temporary.open('xb') as stream:
            created = True
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in sorted({native_name: native, hd_name: hd,
                        'manifest.json': json.dumps(manifest, sort_keys=True).encode(),
                        'licenses/ReTuned-Dialogue-OFL.txt': Path(license_path).read_bytes()}.items()):
                    info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, data)
        temporary.replace(output)
    except BaseException:
        if created:
            temporary.unlink(missing_ok=True)
        raise
    return manifest


def read_styles(directory):
    """Read the two shipped faces with a pinned integrity and layout contract."""
    directory = Path(directory)
    contract = json.loads((directory/'ReTunedDialogue-Styles.json').read_text())
    if set(contract['styles']) != {'regular', 'bold'} or contract['license'] != 'OFL-1.1':
        raise ValueError('Invalid bundled dialogue styles')
    result = {}
    for style, record in contract['styles'].items():
        data = {}
        for field in ('native', 'coverage'):
            name = record[field]['file']
            if Path(name).name != name or '\\' in name:
                raise ValueError('Invalid bundled font path')
            payload = (directory/name).read_bytes()
            if hashlib.sha256(payload).hexdigest() != record[field]['sha256']:
                raise ValueError('Bundled dialogue font integrity check failed')
            parse(payload)
            data[field] = payload
        result[style] = data
    return result


def pair_styles(source_native, directory, output):
    """Pair both licensed faces with the exact local font they may replace.

    The original native image is a local identity check, not a public asset.
    Runtime replacement requires the same directory, cell and allocation bounds.
    """
    directory, output = Path(directory), Path(output)
    source_records, _, source_fallback, sw, sh, so = parse(source_native)
    styles = read_styles(directory)
    source_name = 'sources/' + hashlib.sha256(source_native).hexdigest() + '.qbf'
    entries = {source_name: source_native}
    fonts = []
    with tempfile.TemporaryDirectory() as temp:
        for style, data in sorted(styles.items()):
            records, _, fallback, w, h, offset = parse(data['native'])
            if (len(data['native']) > len(source_native) or (w,h,fallback,offset) != (sw,sh,source_fallback,so)
                    or [r[0] for r in records] != [r[0] for r in source_records]):
                raise ValueError('Bundled font layout is incompatible with this native font')
            path = Path(temp)/(style+'.zip')
            manifest = pair(data['native'], data['coverage'], path, directory/'LICENSE.txt')
            font = manifest['fonts'][0]
            font['style'] = style
            fonts.append(font)
            with zipfile.ZipFile(path) as archive:
                for name in archive.namelist():
                    if name != 'manifest.json':
                        entries[name] = archive.read(name)
    manifest.update(fonts=fonts, default_style='bold',
                    native_sources=[source_name], private_local_artifact=True, redistributable=False)
    entries['manifest.json'] = json.dumps(manifest, sort_keys=True).encode()
    if output.exists() or output.is_symlink():
        raise ValueError('Refusing to overwrite font choice pack')
    temporary = output.with_name(output.name+'.partial')
    created = False
    try:
        with temporary.open('xb') as stream:
            created = True
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in sorted(entries.items()):
                    info = zipfile.ZipInfo(name, (2026,1,1,0,0,0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, data)
        temporary.replace(output)
    except BaseException:
        if created:
            temporary.unlink(missing_ok=True)
        raise
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--typeface', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.typeface, args.output), indent=2))
