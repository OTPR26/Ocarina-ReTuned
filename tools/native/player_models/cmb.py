"""Local CMB model analysis (OoT3D v6 and MM3D v10). No game assets embedded."""

import struct, math
import numpy as np
from .reader import require

U = lambda d, o: struct.unpack_from("<I", d, o)[0]
H = lambda d, o: struct.unpack_from("<H", d, o)[0]
S = lambda d, o: struct.unpack_from("<h", d, o)[0]
F = lambda d, o: struct.unpack_from("<f", d, o)[0]


def put(d, o, v, fmt="I"):
    struct.pack_into("<" + fmt, d, o, v)


def chunk(tag, data):
    return tag + struct.pack("<I", len(data) + 8) + data


def align(d, n=4):
    d.extend(b"\0" * (-len(d) % n))
    return len(d)


DT = {
    0x1400: np.dtype("i1"),
    0x1401: np.dtype("u1"),
    0x1402: np.dtype("<i2"),
    0x1403: np.dtype("<u2"),
    0x1404: np.dtype("<i4"),
    0x1405: np.dtype("<u4"),
    0x1406: np.dtype("<f4"),
}


class Model:
    def __init__(self, data):
        self.data = bytes(data)
        d = self.data
        self.version = U(d, 8)
        require(self.version in (6, 10), "Unsupported native model version")
        self.mm = self.version == 10
        self.attrs = 9 if self.mm else 8
        self.stride = 0x2C if self.mm else 0x28
        keys = (
            [
                "skl",
                "qtrs",
                "mats",
                "tex",
                "sklm",
                "luts",
                "vatr",
                "indices",
                "textures",
            ]
            if self.mm
            else ["skl", "mats", "tex", "sklm", "luts", "vatr", "indices", "textures"]
        )
        self.offsets = dict(
            zip(keys, struct.unpack_from("<" + "I" * len(keys), d, 0x24))
        )
        self.chunks = {
            k: d[o : o + U(d, o + 4)]
            for k, o in self.offsets.items()
            if k not in ("indices", "textures")
        }
        # Grezzo's material length field omits part of the shared combiner table.
        self.chunks["mats"] = d[self.offsets["mats"] : self.offsets["tex"]]
        self.chunks["indices"] = d[self.offsets["indices"] : self.offsets["textures"]]
        self.chunks["textures"] = d[self.offsets["textures"] :]
        self.materials = []
        m = self.chunks["mats"]
        stride = 0x16C if self.mm else 0x15C
        for i in range(U(m, 8)):
            self.materials.append(m[12 + i * stride : 12 + (i + 1) * stride])
        self.combiners = m[12 + len(self.materials) * stride :]
        self.tex = [
            self.chunks["tex"][12 + i * 36 : 48 + i * 36]
            for i in range(U(self.chunks["tex"], 8))
        ]
        v = self.chunks["vatr"]
        self.buffers = [
            v[U(v, 16 + i * 8) : U(v, 16 + i * 8) + U(v, 12 + i * 8)]
            for i in range(self.attrs)
        ]
        sk = self.chunks["sklm"]
        mo = U(sk, 8)
        so = U(sk, 12)
        self.mesh_header = sk[mo : mo + 16]
        self.shape_header = sk[so : so + 16]
        self.meshes = [
            sk[
                mo
                + 16
                + i * (12 if self.mm else 4) : mo
                + 16
                + (i + 1) * (12 if self.mm else 4)
            ]
            for i in range(U(sk, mo + 8))
        ]
        self.shapes = []
        for i in range(U(sk, so + 8)):
            o = so + H(sk, so + 16 + i * 2)
            self.shapes.append(sk[o : o + U(sk, o + 4)])
        self.world = []
        s = self.chunks["skl"]
        self.parents = []
        for i in range(U(s, 8)):
            o = 16 + i * self.stride
            parent = S(s, o + 2)
            self.parents.append(parent)
            sx, sy, sz, rx, ry, rz, tx, ty, tz = struct.unpack_from("<9f", s, o + 4)
            cx, snx = math.cos(rx), math.sin(rx)
            cy, sny = math.cos(ry), math.sin(ry)
            cz, snz = math.cos(rz), math.sin(rz)
            x = np.array([[1, 0, 0], [0, cx, -snx], [0, snx, cx]])
            y = np.array([[cy, 0, sny], [0, 1, 0], [-sny, 0, cy]])
            z = np.array([[cz, -snz, 0], [snz, cz, 0], [0, 0, 1]])
            mat = np.eye(4)
            mat[:3, :3] = z @ y @ x @ np.diag([sx, sy, sz])
            mat[:3, 3] = [tx, ty, tz]
            if parent >= 0:
                mat = self.world[parent] @ mat
            self.world.append(mat)

    def descriptor(self, shape, i):
        return shape[0x24 + i * 28 : 0x40 + i * 28]

    def values(self, shape, i, n, dim):
        desc = self.descriptor(shape, i)
        start = U(desc, 0)
        scale = F(desc, 4)
        typ = H(desc, 8)
        mode = H(desc, 10)
        if mode == 1:
            return np.tile(np.array(struct.unpack_from("<4f", desc, 12)[:dim]), (n, 1))
        require(mode == 0, "Unsupported native vertex descriptor")
        return (
            np.frombuffer(self.buffers[i], dtype=DT[typ], count=n * dim, offset=start)
            .reshape(n, dim)
            .astype(float)
            * scale
        )

    def primitives(self, shape):
        base = 0x124 if self.mm else 0x108
        prims = []
        for i in range(H(shape, 8)):
            o = H(shape, base + i * 2)
            p = shape[o : o + U(shape, o + 4)]
            require(p[:4] == b"prms", "Invalid native primitive")
            b = U(p, 16)
            bones = list(struct.unpack_from("<" + "H" * H(p, 14), p, b))
            r = U(p, 20)
            count = H(p, r + 20)
            at = H(p, r + 22) * 2
            dtype = DT[H(p, r + 16)]
            indices = np.frombuffer(
                self.chunks["indices"], dtype=dtype, count=count, offset=at
            ).astype(int)
            prims.append((o, p, H(p, 12), bones, indices))
        return prims

    def geometry(self, si):
        sh = self.shapes[si]
        pr = self.primitives(sh)
        n = 1 + max(int(max(p[4])) for p in pr if len(p[4]))
        dim = H(sh, 0x120 if self.mm else 0x104)
        pos = self.values(sh, 0, n, 3)
        norm = self.values(sh, 1, n, 3)
        uv = self.values(sh, 4 if self.mm else 3, n, 2)
        bi = self.values(sh, 7 if self.mm else 6, n, dim).astype(int)
        bw = self.values(sh, 8 if self.mm else 7, n, dim)
        return pos, norm, uv, bi, bw, pr

    def world_geometry(self, si):
        pos, norm, uv, bi, bw, pr = self.geometry(si)
        out = pos.copy()
        for _, _, mode, bones, idx in pr:
            for vi in np.unique(idx):
                if mode == 2:
                    continue
                bone = bones[0 if mode == 0 else bi[vi, 0]]
                out[vi] = (self.world[bone] @ np.r_[pos[vi], 1])[:3]
        return out, uv, pr
