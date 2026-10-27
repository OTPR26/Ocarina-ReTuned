from .cmb import U, H, S, align, put
from .reader import require


def validate_materials(model):
    # Some Grezzo files declare a short mats length; validate the complete shared
    # table through tex offset, rather than trusting that legacy length field.
    operations = {
        0x1E01,
        0x2100,
        0x104,
        0x8574,
        0x8575,
        0x84E7,
        0x86AE,
        0x86AF,
        0x6401,
        0x6402,
    }
    for material in model.materials:
        require(U(material, 0x120) <= 6, "Too many material combiner stages")
        for j in range(U(material, 0x120)):
            offset = H(material, 0x124 + j * 2) * 40
            require(offset + 40 <= len(model.combiners), "Truncated material combiner table")
            require(H(model.combiners, offset) in operations, "Invalid RGB combiner operation")
            require(H(model.combiners, offset + 2) in operations, "Invalid alpha combiner operation")
        for j in range(3):
            require(-1 <= S(material, 16 + j * 24) < len(model.tex), "Invalid material texture index")


def repack_gar(gar, filename, replacement):
    from .binary import entries

    es = list(entries(gar))
    meta = U(gar, 16)
    offsets = U(gar, 20)
    out = bytearray(gar[: min(e[1] for e in es)])
    for i, (name, oldoff, payload) in enumerate(es):
        align(out, 4)
        put(out, offsets + i * 4, len(out))
        data = replacement if name == filename else payload
        put(out, meta + i * (12 if gar[:4] == b"GAR\2" else 8), len(data))
        out.extend(data)
    put(out, 4, len(out))
    checked = dict((n, p) for n, _, p in entries(out))
    require(checked[filename] == replacement, "Actor replacement did not round-trip")
    for name, _, payload in es:
        if name != filename:
            require(checked[name] == payload, "Unrelated actor resource changed")
    return bytes(out)

