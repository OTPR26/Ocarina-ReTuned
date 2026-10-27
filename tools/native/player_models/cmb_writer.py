"""Emit rigid human meshes into a user-supplied OoT3D actor, preserving equipment."""

import hashlib
import struct
import numpy as np
from .cmb import Model, U, H, put, chunk, align
from .binary import entries
from .packing import repack_gar, validate_materials
from .geometry import encode
from .reader import require


def descriptor(start=0, typ=0x1406, constant=None):
    return struct.pack(
        "<IfHH4f",
        start,
        1.0,
        typ,
        int(constant is not None),
        *(constant if constant is not None else (0, 0, 0, 0))
    )


class Writer:
    def __init__(self, actor, age):
        self.actor = actor
        self.gar = actor
        require(age in ("child", "adult"), "Choose child or adult")
        self.model_name = "child/model/childlink_v2.cmb" if age == "child" else "boy/model/link_v2.cmb"
        self.body_groups = (24, 25) if age == "child" else (45,)
        self.head_groups = (26,) if age == "child" else (46,)
        replaced_groups = (*self.body_groups, *self.head_groups, *((47,) if age == "adult" else ()))
        self.body_material = 2 if age == "child" else 0
        hand_material = 16 if age == "child" else 22
        self.native = Model(
            dict((n, d) for n, _, d in entries(self.gar))[self.model_name]
        )
        m = self.native
        require(m.version == 6 and len(m.world) == 25, "Unsupported native player model")
        self.shape_template = next(H(me, 0) for me in m.meshes if me[3] == self.body_groups[0])
        self.buffers = [bytearray(b) for b in m.buffers]
        self.indices = bytearray(m.chunks["indices"])
        self.shapes = list(m.shapes)
        self.materials = list(m.materials)
        self.textures = list(m.tex)
        self.texdata = bytearray(m.chunks["textures"])
        self.templates = {me[3]: me for me in m.meshes}
        self.hand_groups = {"left": set(), "right": set()}
        self.meshes = []
        for mesh in m.meshes:
            bones = {
                b for _, _, _, bb, _ in m.primitives(m.shapes[H(mesh, 0)]) for b in bb
            }
            side = (
                "left" if bones <= {15, 16} else "right" if bones <= {19, 20} else None
            )
            if side and mesh[2] == hand_material:
                self.hand_groups[side].add(mesh[3])
            elif mesh[3] not in replaced_groups and mesh[2] != 1:
                self.meshes.append(mesh)
        self.material_cache = {}
        self.triangles = 0

    def material(self, image, wrap_s, wrap_t):
        image = np.ascontiguousarray(image, dtype=np.uint8)
        h, w, _ = image.shape
        require(
            w >= 8
            and h >= 8
            and w <= 1024
            and h <= 1024
            and w & (w - 1) == 0
            and h & (h - 1) == 0,
            "Unsupported converted texture dimensions",
        )
        key = (hashlib.sha256(image.tobytes()).digest(), w, h, wrap_s, wrap_t)
        if key in self.material_cache:
            return self.material_cache[key]
        require(len(self.materials) < 256, "Model exceeds native material limit")
        # PICA texture storage starts at the bottom image row.
        raw = encode(image[::-1].copy())
        require(len(self.texdata) + len(raw) <= 64 * 1024 * 1024, "Converted textures exceed 64 MiB")
        tex = bytearray(self.native.tex[2])
        put(tex, 0, len(raw))
        put(tex, 4, 1)
        put(tex, 6, 1, "H")
        put(tex, 8, w, "H")
        put(tex, 10, h, "H")
        put(tex, 12, 0x14016752)
        put(tex, 16, align(self.texdata, 128))
        tex[20:36] = ("zobj_" + str(len(self.textures))).encode().ljust(16, b"\0")
        ti = len(self.textures)
        self.textures.append(tex)
        self.texdata.extend(raw)
        mat = bytearray(self.native.materials[self.body_material])
        put(mat, 16, ti, "h")
        # Preserve native back-face culling. Imported triangles use the same
        # outward winding as the native lit meshes.
        mat[4] = self.native.materials[self.body_material][4]
        # GL clamp-to-edge, mirror-repeat and repeat, respectively.
        wrap = lambda mode: 0x812F if mode & 2 else 0x8370 if mode & 1 else 0x2901
        put(mat, 24, wrap(wrap_s), "H")
        put(mat, 26, wrap(wrap_t), "H")
        mat[0x130] = 1
        mat[0x131] = 8
        put(mat, 0x132, 0x204, "H")
        mi = len(self.materials)
        self.materials.append(mat)
        self.material_cache[key] = mi
        return mi

    def append(self, vertices, triangles, material, groups):
        m = self.native
        batches = []
        current = []
        palette = set()
        for tri in triangles:
            bs = {vertices[i]["bone"] for i in tri}
            if current and (len(palette | bs) > 10 or len(current) >= 4000):
                batches.append(current)
                current = []
                palette = set()
            current.append(tri)
            palette |= bs
        if current:
            batches.append(current)
        for tris in batches:
            ids = sorted({i for tri in tris for i in tri})
            remap = {n: i for i, n in enumerate(ids)}
            vv = [vertices[i] for i in ids]
            bones = sorted({v["bone"] for v in vv})
            bone_map = {b: i for i, b in enumerate(bones)}
            rows = {
                0: [v["pos"] for v in vv],
                1: [v["normal"] for v in vv],
                2: [v["color"] for v in vv],
                3: [v["uv"] for v in vv],
                6: [[bone_map[v["bone"]]] for v in vv],
                7: [[100] for v in vv],
            }
            # Use OoT3D's normal lit rigid path when N64 vertex colours are white.
            # Coloured display lists retain an explicit colour array.
            has_colors = any(not np.allclose(v["color"], [1, 1, 1, 1]) for v in vv)
            if not has_colors:
                del rows[2]
            sh = bytearray(m.shapes[self.shape_template][:0x108])
            put(sh, 8, 1, "H")
            put(sh, 10, 0x4F if has_colors else 0x4B, "H")
            sh[12:24] = struct.pack("<3f", *np.array(rows[0]).mean(0))
            put(sh, 0x104, 1, "H")
            for attr in range(8):
                if attr in rows:
                    at = align(self.buffers[attr])
                    typ = 0x1401 if attr in (6, 7) else 0x1406
                    dt = "u1" if attr in (6, 7) else "<f4"
                    array = np.array(rows[attr], dtype=dt)
                    require(np.isfinite(array).all(), "Nonfinite converted vertex data")
                    self.buffers[attr].extend(array.tobytes())
                    sh[0x24 + attr * 28 : 0x40 + attr * 28] = descriptor(at, typ)
                    if attr == 7:
                        put(sh, 0x24 + attr * 28 + 4, 0.01, "f")
                else:
                    sh[0x24 + attr * 28 : 0x40 + attr * 28] = descriptor(
                        constant=[1, 1, 1, 1] if attr == 2 else [0, 0, 0, 0]
                    )
            sh.extend(struct.pack("<H", 0x10C))
            align(sh)
            bs = bytearray(struct.pack("<" + "H" * len(bones), *bones))
            align(bs)
            prm = bytearray(m.primitives(m.shapes[self.shape_template])[0][1][-24:])
            start = align(self.indices, 2) // 2
            flat = [remap[i] for tri in tris for i in tri]
            require(
                start < 65536 and len(flat) < 65536, "Model exceeds native index limit"
            )
            self.indices.extend(np.array(flat, dtype="<u2").tobytes())
            put(prm, 16, 0x1403, "H")
            put(prm, 20, len(flat), "H")
            put(prm, 22, start, "H")
            pr = bytearray(b"prms" + bytes(20))
            put(pr, 8, 1)
            put(pr, 12, 1, "H")
            put(pr, 14, len(bones), "H")
            put(pr, 16, 24)
            put(pr, 20, 24 + len(bs))
            pr.extend(bs)
            pr.extend(prm)
            put(pr, 4, len(pr))
            sh.extend(pr)
            put(sh, 4, len(sh))
            si = len(self.shapes)
            self.shapes.append(sh)
            for group in groups:
                mesh = bytearray(self.templates[group])
                put(mesh, 0, si, "H")
                mesh[2] = material
                self.meshes.append(mesh)
            self.triangles += len(tris)

    def finish(self):
        m = self.native
        transparent = {(H(me, 0), me[2]) for me in m.meshes[H(m.mesh_header, 12) :]}
        self.meshes.sort(key=lambda me: ((H(me, 0), me[2]) in transparent, me[2]))
        msh = bytearray(m.mesh_header)
        put(msh, 8, len(self.meshes))
        put(
            msh,
            12,
            sum((H(me, 0), me[2]) not in transparent for me in self.meshes),
            "H",
        )
        msh.extend(b"".join(self.meshes))
        put(msh, 4, len(msh))
        shp = bytearray(m.shape_header)
        put(shp, 8, len(self.shapes))
        shp.extend(bytes(len(self.shapes) * 2))
        align(shp)
        for i, shape in enumerate(self.shapes):
            require(len(shp) < 65536, "Model exceeds native shape-table limit")
            put(shp, 16 + i * 2, len(shp), "H")
            shp.extend(shape)
            align(shp)
        put(shp, 4, len(shp))
        vatr = bytearray(b"vatr" + bytes(68))
        put(vatr, 8, len(self.buffers[0]) // 12)
        for i, buf in enumerate(self.buffers):
            align(vatr)
            put(vatr, 12 + i * 8, len(buf))
            put(vatr, 16 + i * 8, len(vatr))
            vatr.extend(buf)
        put(vatr, 4, len(vatr))
        mats = bytearray(
            chunk(
                b"mats",
                struct.pack("<I", len(self.materials))
                + b"".join(self.materials)
                + m.combiners,
            )
        )
        put(mats, 4, len(mats))
        chunks = {
            **m.chunks,
            "sklm": chunk(b"sklm", struct.pack("<II", 16, 16 + len(msh)) + msh + shp),
            "vatr": vatr,
            "mats": mats,
            "tex": chunk(
                b"tex ", struct.pack("<I", len(self.textures)) + b"".join(self.textures)
            ),
            "indices": self.indices,
            "textures": self.texdata,
        }
        out = bytearray(m.data[:0x48])
        put(out, 0x20, len(self.indices) // 2)
        for i, key in enumerate(
            (
                "skl",
                "mats",
                "tex",
                "sklm",
                "luts",
                "vatr",
                "indices",
                "textures",
            )
        ):
            align(out, 128 if key == "textures" else 4)
            put(out, 0x24 + i * 4, len(out))
            out.extend(chunks[key])
        put(out, 4, len(out))
        test = Model(out)
        validate_materials(test)
        require(test.chunks["skl"] == m.chunks["skl"], "Native skeleton changed")
        for i in range(len(test.shapes)):
            pos, normal, uv, bi, bw, pr = test.geometry(i)
            require(
                np.isfinite(pos).all()
                and np.isfinite(normal).all()
                and np.isfinite(uv).all(),
                "Converted model contains invalid geometry",
            )
            for _, _, mode, bones, idx in pr:
                require(
                    len(bones) <= 10 and int(idx.max()) < len(pos),
                    "Invalid native primitive",
                )
        return repack_gar(self.gar, self.model_name, out), bytes(out)
