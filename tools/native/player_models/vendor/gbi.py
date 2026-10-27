"""
Minimal F3DEX2 display-list interpreter for Zelda64 player-model zobjs.

Walks a display list starting at a segmented address, following G_DL calls,
and records:
  - vertex loads (into a 32-slot vertex cache),
  - triangles (as (texture_state, (v0,v1,v2)) with resolved vertex data),
  - the current texture / tile / TLUT state at each triangle.

Geometry is extracted in each DL's LOCAL space (matrices are not applied here);
the caller poses limbs using the skeleton's bind-pose transforms.
"""
from __future__ import annotations
import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# opcodes (F3DEX2)
G_VTX = 0x01
G_MODIFYVTX = 0x02
G_CULLDL = 0x03
G_BRANCH_Z = 0x04
G_TRI1 = 0x05
G_TRI2 = 0x06
G_QUAD = 0x07
G_DL = 0xDE
G_ENDDL = 0xDF
G_SETOTHERMODE_H = 0xE3
G_SETOTHERMODE_L = 0xE2
G_RDPHALF_1 = 0xE1
G_RDPHALF_2 = 0xF1
G_TEXTURE = 0xD7
G_SETTIMG = 0xFD
G_SETTILE = 0xF5
G_SETTILESIZE = 0xF2
G_LOADBLOCK = 0xF3
G_LOADTILE = 0xF4
G_LOADTLUT = 0xF0
G_SETPRIMCOLOR = 0xFA
G_SETENVCOLOR = 0xFB
G_SETCOMBINE = 0xFC
G_GEOMETRYMODE = 0xD9
G_MTX = 0xDA


@dataclass
class Vertex:
    x: int; y: int; z: int
    s: int; t: int
    r: int; g: int; b: int; a: int   # or normal xyz + alpha
    flex_slot: int = -1              # seg-0x0D flex matrix slot (-1 = limb's own)


@dataclass
class TileState:
    timg_addr: int = 0        # segmented address of texture image
    fmt: int = 0
    siz: int = 0
    line: int = 0
    width: int = 0
    height: int = 0
    cms: int = 0              # clamp/wrap/mirror S
    cmt: int = 0
    tlut_addr: int = 0
    tlut_count: int = 0
    prim: Tuple[int, int, int, int] = (255, 255, 255, 255)
    env: Tuple[int, int, int, int] = (255, 255, 255, 255)
    # combiner colour-source usage (for faithful tint) and RDP tile UV params
    combine_uses_prim: bool = False
    combine_uses_env: bool = False
    combine_uses_tex: bool = True   # False = prim/shade-only (ignore bound texture)
    combine_alpha_uses_tex: bool = True  # False = alpha from shade/prim, not texel
    combine_alpha_uses_prim: bool = False  # alpha driven by PRIM alpha (translucency)
    combine_alpha_uses_env: bool = False   # alpha driven by ENV alpha
    shift_s: int = 0
    shift_t: int = 0
    masks: int = 0
    maskt: int = 0
    uls: int = 0
    ult: int = 0
    lit: bool = True          # G_LIGHTING: vtx bytes 12-14 are a normal, else baked colour
    # captured raw render-state command words (w0,w1), replayed on export
    combine: Tuple[int, int] = (0, 0)
    othermode_h: Tuple[int, int] = (0, 0)
    othermode_l: Tuple[int, int] = (0, 0)
    geometrymode: tuple = ()          # sequence of (w0,w1) - accumulates, replay all
    texture: Tuple[int, int] = (0, 0)

    def key(self):
        return (self.timg_addr, self.fmt, self.siz, self.width, self.height,
                self.cms, self.cmt, self.tlut_addr)


@dataclass
class Triangle:
    v: Tuple[Vertex, Vertex, Vertex]
    tile: TileState


@dataclass
class DLResult:
    triangles: List[Triangle] = field(default_factory=list)
    used_textures: set = field(default_factory=set)


def seg_off(addr: int) -> Tuple[int, int]:
    return (addr >> 24) & 0xFF, addr & 0x00FFFFFF


class Interp:
    def __init__(self, seg_map: Dict[int, bytes]):
        self.seg = seg_map
        self.vtx: List[Optional[Vertex]] = [None] * 32
        self.tile = TileState()
        # pending texture image set by G_SETTIMG; only becomes the *bound* image on
        # G_LOADBLOCK/G_LOADTILE, and the *palette* on G_LOADTLUT. Tracking this
        # separately matters for CI textures whose DLs do SETTIMG(tex) LOADBLOCK
        # SETTIMG(pal) LOADTLUT - the last SETTIMG is the palette, not the image.
        self._pend_timg = 0
        self._pend_fmt = 0
        self._pend_siz = 0
        self._geom = []          # accumulated G_GEOMETRYMODE (w0,w1) history
        self._cur_flex = -1      # current seg-0x0D flex matrix slot
        self.result = DLResult()
        self._visited = set()
        self._commands = 0

    def _read(self, addr: int, length: int) -> bytes:
        s, o = seg_off(addr)
        buf = self.seg.get(s)
        if buf is None:
            return b""
        return buf[o:o + length]

    def _load_vtx(self, w0: int, w1: int):
        n = (w0 >> 12) & 0xFF
        vend = (w0 >> 1) & 0x7F
        v0 = vend - n
        raw = self._read(w1, n * 16)
        for i in range(n):
            base = i * 16
            if base + 16 > len(raw):
                break
            x, y, z, flag, s, t, r, g, b, a = struct.unpack_from(">hhhHhhBBBB", raw, base)
            slot = v0 + i
            if 0 <= slot < 32:
                self.vtx[slot] = Vertex(x, y, z, s, t, r, g, b, a, self._cur_flex)

    def _emit_tri(self, a: int, b: int, c: int):
        if not (0 <= a < 32 and 0 <= b < 32 and 0 <= c < 32):
            return
        va, vb, vc = self.vtx[a], self.vtx[b], self.vtx[c]
        if va and vb and vc:
            ts = TileState(**{k: getattr(self.tile, k) for k in self.tile.__dataclass_fields__})
            self.result.triangles.append(Triangle((va, vb, vc), ts))
            if ts.timg_addr:
                self.result.used_textures.add(ts.key())

    def run(self, start_addr: int, depth: int = 0):
        if depth > 40:
            return
        s, o = seg_off(start_addr)
        buf = self.seg.get(s)
        if buf is None:
            return
        p = o
        while p + 8 <= len(buf):
            self._commands += 1
            if self._commands > 1000000 or len(self.result.triangles) > 100000:
                raise ValueError("Display-list budget exceeded")
            w0, w1 = struct.unpack_from(">II", buf, p)
            op = (w0 >> 24) & 0xFF
            p += 8
            if op == G_ENDDL:
                break
            elif op == G_VTX:
                self._load_vtx(w0, w1)
            elif op == G_TRI1:
                a = ((w0 >> 16) & 0xFF) // 2
                b = ((w0 >> 8) & 0xFF) // 2
                c = (w0 & 0xFF) // 2
                self._emit_tri(a, b, c)
            elif op == G_TRI2:
                a = ((w0 >> 16) & 0xFF) // 2
                b = ((w0 >> 8) & 0xFF) // 2
                c = (w0 & 0xFF) // 2
                d = ((w1 >> 16) & 0xFF) // 2
                e = ((w1 >> 8) & 0xFF) // 2
                f = (w1 & 0xFF) // 2
                self._emit_tri(a, b, c)
                self._emit_tri(d, e, f)
            elif op == G_QUAD:
                a = ((w0 >> 16) & 0xFF) // 2
                b = ((w0 >> 8) & 0xFF) // 2
                c = (w0 & 0xFF) // 2
                d = (w1 & 0xFF) // 2
                self._emit_tri(a, b, c)
                self._emit_tri(a, c, d)
            elif op == G_SETTIMG:
                self._pend_timg = w1
                self._pend_fmt = (w0 >> 21) & 0x7
                self._pend_siz = (w0 >> 19) & 0x3
            elif op in (G_LOADBLOCK, G_LOADTILE):
                # the pending SETTIMG image is now the bound render texture
                self.tile.timg_addr = self._pend_timg
                self.tile.fmt = self._pend_fmt
                self.tile.siz = self._pend_siz
            elif op == G_SETTILE:
                # only track tile 0 (rendering tile)
                tile = (w1 >> 24) & 0x7
                if tile == 0:
                    self.tile.fmt = (w0 >> 21) & 0x7
                    self.tile.siz = (w0 >> 19) & 0x3
                    self.tile.line = (w0 >> 9) & 0x1FF
                    self.tile.cmt = (w1 >> 18) & 0x3
                    self.tile.cms = (w1 >> 8) & 0x3
                    self.tile.masks = (w1 >> 4) & 0xF
                    self.tile.maskt = (w1 >> 14) & 0xF
                    self.tile.shift_s = w1 & 0xF
                    self.tile.shift_t = (w1 >> 10) & 0xF
            elif op == G_SETTILESIZE:
                tile = (w1 >> 24) & 0x7
                if tile == 0:
                    uls = (w0 >> 12) & 0xFFF
                    ult = w0 & 0xFFF
                    lrs = (w1 >> 12) & 0xFFF
                    lrt = w1 & 0xFFF
                    self.tile.uls = uls
                    self.tile.ult = ult
                    self.tile.width = ((lrs - uls) >> 2) + 1
                    self.tile.height = ((lrt - ult) >> 2) + 1
                    # physical (loaded) size can be smaller than the render span for a
                    # wrapping/mirroring tile: the real size is 1<<mask (ObjectModelReader parity)
                    mw, mh = self.tile.masks, self.tile.maskt
                    if 1 <= mw <= 8 and (1 << mw) < self.tile.width and not (self.tile.cms & 0x2):
                        self.tile.width = 1 << mw
                    if 1 <= mh <= 8 and (1 << mh) < self.tile.height and not (self.tile.cmt & 0x2):
                        self.tile.height = 1 << mh
            elif op == G_LOADTLUT:
                self.tile.tlut_addr = self._pend_timg
                self.tile.tlut_count = (((w1 >> 14) & 0x3FF) + 1)
            elif op == G_SETPRIMCOLOR:
                self.tile.prim = ((w1 >> 24) & 0xFF, (w1 >> 16) & 0xFF,
                                  (w1 >> 8) & 0xFF, w1 & 0xFF)
            elif op == G_SETENVCOLOR:
                self.tile.env = ((w1 >> 24) & 0xFF, (w1 >> 16) & 0xFF,
                                 (w1 >> 8) & 0xFF, w1 & 0xFF)
            elif op == G_SETCOMBINE:
                self.tile.combine = (w0, w1)
                a0 = (w0 >> 20) & 0xF; c0 = (w0 >> 15) & 0x1F
                b0 = (w1 >> 28) & 0xF; dd0 = (w1 >> 15) & 0x7
                a1 = (w0 >> 5) & 0xF; c1 = w0 & 0x1F
                b1 = (w1 >> 24) & 0xF; dd1 = (w1 >> 6) & 0x7
                self.tile.combine_uses_prim = 3 in (a0, c0, a1, c1, dd0, dd1)
                self.tile.combine_uses_env = 5 in (a0, c0, a1, c1, dd0, dd1)
                # TEXEL0(=1)/TEXEL1(=2) anywhere in the colour combiner -> the tile
                # actually samples its texture. Prim/shade-only skin combiners do NOT,
                # so a texture merely left bound by a previous limb must be ignored
                # (else it darkens e.g. the pale face by whatever was last loaded).
                self.tile.combine_uses_tex = any(
                    x in (1, 2) for x in (a0, b0, c0, dd0, a1, b1, c1, dd1))
                # Alpha combiner sources: TEXEL0/1 alpha (=1/2) anywhere means the
                # texture's alpha actually drives transparency (hair/leaf cutouts).
                # If not, alpha is shade/prim (opaque) and a 0-alpha texture must NOT
                # vanish the surface (e.g. shoes/shirt/socks going invisible).
                Aa0 = (w0 >> 12) & 0x7; Ac0 = (w0 >> 9) & 0x7
                Ab0 = (w1 >> 12) & 0x7; Ad0 = (w1 >> 9) & 0x7
                Aa1 = (w1 >> 21) & 0x7; Ac1 = (w1 >> 18) & 0x7
                Ab1 = (w1 >> 3) & 0x7; Ad1 = w1 & 0x7
                asrc = (Aa0, Ab0, Ac0, Ad0, Aa1, Ab1, Ac1, Ad1)
                self.tile.combine_alpha_uses_tex = any(x in (1, 2) for x in asrc)
                self.tile.combine_alpha_uses_prim = 3 in asrc   # PRIM alpha -> translucency
                self.tile.combine_alpha_uses_env = 5 in asrc
            elif op == G_SETOTHERMODE_H:
                self.tile.othermode_h = (w0, w1)
            elif op == G_SETOTHERMODE_L:
                self.tile.othermode_l = (w0, w1)
            elif op == G_GEOMETRYMODE:
                self._geom.append((w0, w1))
                self.tile.geometrymode = tuple(self._geom)
                # track G_LIGHTING (0x20000): set-word (w1) turns it on, clear-word off
                if w1 & 0x00020000:
                    self.tile.lit = True
                elif not (w0 & 0x00020000):   # cleared by this command
                    self.tile.lit = False
            elif op == G_TEXTURE:
                self.tile.texture = (w0, w1)
            elif op == G_MTX:
                # flex skeleton: G_MTX from segment 0x0D switches to another
                # limb's matrix (slot = offset/0x40) for the vertices that follow.
                if (w1 >> 24) & 0xFF == 0x0D:
                    self._cur_flex = (w1 & 0xFFFFFF) // 0x40
            elif op == G_DL:
                push = ((w0 >> 16) & 0xFF) == 0
                self.run(w1, depth + 1)
                if not push:
                    break  # branch (no push) ends this list
            elif op == G_BRANCH_Z:
                # next 8 bytes are RDPHALF holding the address; handled crudely:
                pass
        return self.result


    def run_limb(self, start_addr: int, flex_slot: int = -1):
        """Run one limb DL keeping the RDP tile/texture/combiner state from prior
        limbs (state carries across limbs in hardware - some limbs draw with no
        SETTIMG and inherit the previous limb's texture), but with fresh triangle
        output and the limb's own matrix (flex slot reset)."""
        self.result = DLResult()
        self._cur_flex = flex_slot
        self.run(start_addr)
        return self.result.triangles


def walk(seg_map: Dict[int, bytes], start_addr: int) -> DLResult:
    return Interp(seg_map).run(start_addr)
