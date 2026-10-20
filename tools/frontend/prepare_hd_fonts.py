"""Prepare local HD font coverage against the fonts actually used by Reframed.

Only Latin QBF entries are read from the supplied archive. The generated pack
contains user assets and must stay outside source control and public packages.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile


def prepare(engine: Path, romfs: Path, archive: Path, output: Path):
    sys.path.insert(0, str(engine.resolve()))
    from tools.oot3d.decomp_support.scripts.build_topscreen_texture_override_pack import read_level3_romfs_file
    from tools.oot3d.decomp_support.scripts.qbf_font import parse_qbf, pair_font_coverage, MAX_FONT_BYTES

    assets, fonts = {}, []
    with zipfile.ZipFile(archive) as source:
        for region, title in (("eu", "0004000000033600"), ("us", "0004000000033500")):
            name = f"message/{region}/ltn16.qbf"
            try:
                native = parse_qbf(read_level3_romfs_file(romfs, name))
            except FileNotFoundError:
                continue
            suffix = f"/Emulator/load/mods/{title}/romfs/{name}"
            matches = [item for item in source.infolist() if item.filename.endswith(suffix)]
            if len(matches) != 1 or matches[0].file_size > MAX_FONT_BYTES:
                raise ValueError(f"Missing, ambiguous or oversized HD font: {name}")
            coverage = parse_qbf(source.read(matches[0]))
            if (coverage.width, coverage.height) != (64, 64):
                raise ValueError("Expected 64x64 Latin coverage")
            contract = pair_font_coverage(native, coverage)
            original_path = f"native/{native.sha256}.qbf"
            coverage_path = f"coverage/{coverage.sha256}.qbf"
            assets[original_path], assets[coverage_path] = native.data, coverage.data
            fonts.append({"romfs_path": name, "native_file": original_path,
                          "coverage_file": coverage_path, **contract})
    if not fonts:
        raise ValueError("No supported Latin font in the supplied RomFS")
    manifest = {"format": "oot3d_qbf_coverage_v1", "runtime_enabled": True,
                "minimum_output_height": 480, "fonts": fonts,
                "attribution": "TopScreen / Single Screen Experience by M-1 / rlgcarrot"}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".partial")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED) as target:
            for name, payload in sorted(assets.items()):
                target.writestr(zipfile.ZipInfo(name), payload)
            target.writestr(zipfile.ZipInfo("manifest.json"), json.dumps(manifest, sort_keys=True).encode())
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return {"fonts": [{k: v for k, v in f.items() if k != "characters"} for f in fonts],
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("engine", "romfs", "archive", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.engine, args.romfs, args.archive, args.output), indent=2))
