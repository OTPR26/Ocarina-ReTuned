"""Bounded, data-only readers for human-rig .zobj and ModLoader64 .pak inputs."""

import io
import json
from pathlib import Path, PurePosixPath
import struct
import stat
import zipfile
import zlib

LIMIT = 32 * 1024 * 1024


def require(ok, message):
    if not ok:
        raise ValueError(message)


def safe_name(name):
    name = name.replace("\\", "/")
    path = PurePosixPath(name)
    require(
        not path.is_absolute() and ".." not in path.parts and ":" not in name,
        "Unsafe package member name",
    )
    require(bool(name) and "\0" not in name, "Invalid package member name")
    return name


def unpack(path):
    path = Path(path)
    require(not path.is_symlink() and path.is_file(), "Select a regular model file")
    require(0 < path.stat().st_size <= LIMIT, "Model package exceeds 32 MiB")
    data = path.read_bytes()
    if path.suffix.lower() == ".zobj" or data[0x5000:0x500B] == b"MODLOADER64":
        return {path.name if path.suffix.lower() == ".zobj" else "model.zobj": data}
    result = {}
    total = 0
    if zipfile.is_zipfile(io.BytesIO(data)):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            require(len(archive.infolist()) <= 256, "Too many package members")
            for member in archive.infolist():
                safe_name(member.filename)
                require(not member.flag_bits & 1 and not stat.S_ISLNK(member.external_attr >> 16), "Encrypted or linked package member")
                total += member.file_size
                require(total <= LIMIT, "Uncompressed package exceeds 32 MiB")
                if not member.is_dir():
                    name = safe_name(member.filename)
                    require(name not in result, "Duplicate package member")
                    result[name] = archive.read(member)
    else:
        require(data[:11] == b"ModLoader64", "Select a .zobj or ModLoader64 .pak")
        at = 16
        records = []
        while at + 16 <= len(data) and data[at : at + 4] in (b"DEFL", b"UNCO"):
            records.append(
                (data[at : at + 4], *struct.unpack_from(">III", data, at + 4))
            )
            at += 16
            require(len(records) <= 256, "Too many package members")
        require(records, "Empty ModLoader64 package")
        for tag, name_at, start, end in records:
            require(
                at <= name_at < len(data) and at <= start <= end <= len(data),
                "Invalid package member bounds",
            )
            name_end = data.find(b"\xff", name_at)
            require(name_at < name_end <= name_at + 1024, "Invalid package member name")
            name = safe_name(data[name_at:name_end].decode("latin1"))
            blob = data[start:end]
            if tag == b"DEFL":
                decoded = None
                for mode in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
                    try:
                        decoder = zlib.decompressobj(mode)
                        decoded = decoder.decompress(blob, LIMIT - total + 1)
                        require(
                            len(decoded) <= LIMIT - total and decoder.eof,
                            "Package decompression limit exceeded or truncated member",
                        )
                        break
                    except zlib.error:
                        pass
                require(decoded is not None, "Invalid compressed package member")
                blob = decoded
            total += len(blob)
            require(
                total <= LIMIT and name not in result, "Invalid or oversized package"
            )
            result[name] = blob
    return result


def select(path, entry=None, *, age=None):
    files = unpack(path)
    models = {n: d for n, d in files.items() if n.lower().endswith(".zobj")}
    require(models, "Package contains no .zobj models")
    manifest = next(
        (
            json.loads(d)
            for n, d in files.items()
            if PurePosixPath(n).name == "package.json"
        ),
        {},
    )
    if entry:
        matches = [
            (n, d)
            for n, d in models.items()
            if n == entry or PurePosixPath(n).name == entry
        ]
        require(len(matches) == 1, "Requested model entry is missing or ambiguous")
        return *matches[0], manifest
    require(isinstance(manifest, dict), "Invalid model manifest")
    definitions = manifest.get("zzplayas", {})
    require(isinstance(definitions, dict), "Invalid model manifest")
    aliases = ("OOT", "OcarinaOfTime", "OcarinaofTime")
    for game in aliases:
        block = definitions.get(game, {})
        require(isinstance(block, dict), "Invalid model manifest")
        for role in ((age + "_model",) if age else ("child_model", "adult_model")):
            choices = block.get(role, [])
            if isinstance(choices, str):
                choices = [dict(file=choices)] if choices else []
            require(isinstance(choices, list), "Invalid model choices")
            for choice in choices:
                require(isinstance(choice, dict), "Invalid model choice")
                name = choice.get("file")
                matches = [
                    (n, d)
                    for n, d in models.items()
                    if n == name or PurePosixPath(n).name == name
                ]
                if len(matches) == 1:
                    return *matches[0], manifest
    require(not manifest.get("zzplayas"), "Package has no matching OoT model for this age")
    require(len(models) == 1, "Choose a model entry from this multi-model package")
    return *next(iter(models.items())), manifest


def skeleton(data):
    require(
        0x5018 <= len(data) <= LIMIT and data[0x5000:0x500B] == b"MODLOADER64",
        "Unsupported .zobj header",
    )
    # Some MM human exports use ASCII 'h' rather than a numeric form ID.
    require(data[0x500B] in (0, 1, 4, ord("h")),
            "This model uses an unsupported rig. Choose a human Link player model.")
    u32 = lambda at: struct.unpack_from(">I", data, at)[0]

    def offset(pointer, size):
        require(pointer >> 24 == 6, "Skeleton points outside the model segment")
        at = pointer & 0xFFFFFF
        require(at + size <= len(data), "Truncated skeleton")
        return at

    def parse(at):
        require(
            at + 9 <= len(data) and data[at + 4] == 21,
            "Only 21-limb human Link skeletons are supported",
        )
        array = offset(u32(at), 21 * 4)
        limbs = []
        for i in range(21):
            at = offset(u32(array + i * 4), 12)
            x, y, z, child, sibling, dl = struct.unpack_from(">hhhBBI", data, at)
            require(
                child in (*range(21), 255) and sibling in (*range(21), 255),
                "Invalid skeleton hierarchy",
            )
            if dl:
                offset(dl, 8)
            limbs.append(dict(position=(x, y, z), child=child, sibling=sibling, dl=dl))
        order, slots, visited = [], [], set()

        def walk(i):
            while i != 255:
                require(i not in visited, "Cyclic skeleton hierarchy")
                visited.add(i)
                order.append(i)
                if limbs[i]["dl"]:
                    slots.append(i)
                walk(limbs[i]["child"])
                i = limbs[i]["sibling"]

        walk(0)
        require(len(visited) == 21, "Disconnected human skeleton")
        return limbs, order, slots

    try:
        return parse(offset(u32(0x500C), 12))
    except (ValueError, struct.error):
        # Some universal-alias exports omit the direct skeleton pointer.
        for at in range(0x5000, len(data) - 12, 4):
            if data[at + 4] != 21 or data[at] != 6:
                continue
            try:
                return parse(at)
            except (ValueError, struct.error):
                continue
        raise ValueError("No supported human skeleton found")
