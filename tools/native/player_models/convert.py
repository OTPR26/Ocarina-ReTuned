"""Convert human-rig player models using the user's native OoT3D skeleton."""

import collections
from pathlib import Path
import numpy as np
from .geometry import rotation
from .reader import select, skeleton, require
from .cmb_writer import Writer
from .cmb import H
from .vendor.gbi import Interp
from .vendor import n64texture

# Human Link limb roles mapped to the native OoT3D skeleton.
BONES = (1, 2, 2, 6, 7, 8, 3, 4, 5, 9, 11, 12, 9, 14, 15, 16, 18, 19, 20, 21, 9)


def texture(segments, tile):
    if not tile.combine_uses_tex or not tile.timg_addr:
        image = np.full((8, 8, 4), 255, dtype=np.uint8)
    else:
        require(
            0 < tile.width <= 1024 and 0 < tile.height <= 1024,
            "Unsupported N64 tile dimensions",
        )

        def read(address, length):
            segment, offset = address >> 24, address & 0xFFFFFF
            require(
                segment in segments and offset + length <= len(segments[segment]),
                "Texture references external or incomplete data; model needs a shared asset",
            )
            return segments[segment][offset : offset + length]

        length = (tile.width * tile.height * n64texture.SIZ_BITS[tile.siz] + 7) // 8
        raw = read(tile.timg_addr, length)
        tlut = (
            read(tile.tlut_addr, max(tile.tlut_count, 16) * 2) if tile.fmt == 2 else b""
        )
        image = n64texture.decode(
            raw, tile.fmt, tile.siz, tile.width, tile.height, tlut
        )
    tint = (
        tile.prim
        if tile.combine_uses_prim
        else tile.env if tile.combine_uses_env else (255, 255, 255, 255)
    )
    if (
        tile.combine_uses_env
        and not tile.combine_uses_prim
        and tuple(tint) == (255, 255, 255, 255)
    ):
        tint = (30, 105, 27, 255)
    image = image.copy()
    image[:, :, :3] = (
        image[:, :, :3].astype(np.uint16) * np.array(tint[:3], dtype=np.uint16) // 255
    ).astype(np.uint8)
    if not tile.combine_alpha_uses_tex:
        image[:, :, 3] = 255
    if tile.combine_alpha_uses_prim:
        image[:, :, 3] = (
            image[:, :, 3].astype(np.uint16) * tile.prim[3] // 255
        ).astype(np.uint8)
    if tile.combine_alpha_uses_env:
        image[:, :, 3] = (image[:, :, 3].astype(np.uint16) * tile.env[3] // 255).astype(
            np.uint8
        )
    h, w = image.shape[:2]
    ww = max(8, 1 << (w - 1).bit_length())
    hh = max(8, 1 << (h - 1).bit_length())
    if (w, h) != (ww, hh):
        rows = np.minimum((np.arange(hh) + 0.5).astype(float) * h / hh, h - 1).astype(
            int
        )
        columns = np.minimum(
            (np.arange(ww) + 0.5).astype(float) * w / ww, w - 1
        ).astype(int)
        image = image[rows[:, None], columns[None, :]]
    return image


def ground_height(y, knee, sole, target):
    """Fit a lower leg to floor contact without moving its knee."""
    require(knee > sole and knee > target, "Invalid lower-leg contact span")
    factor = (knee - target) / (knee - sole)
    return (knee + (y - knee) * factor, factor) if y < knee else (y, 1.0)


def fit_ground_contact(packets, native, body_groups):
    corrections = []
    for knee_bone, foot_bone in ((4, 5), (7, 8)):
        native_sole = []
        for mesh in native.meshes:
            if mesh[3] not in body_groups:
                continue
            positions, _, _, indices, weights, primitives = native.geometry(H(mesh, 0))
            for _, _, mode, palette, used in primitives:
                for vi in np.unique(used):
                    bone = palette[
                        0 if mode == 0 else indices[vi, int(np.argmax(weights[vi]))]
                    ]
                    if bone == foot_bone:
                        world = (
                            positions[vi]
                            if mode == 2
                            else (native.world[bone] @ np.r_[positions[vi], 1])[:3]
                        )
                        native_sole.append(world[1])
        vertices = [
            v
            for packet in packets.values()
            for v in packet["vertices"]
            if v["bone"] in (knee_bone, foot_bone)
        ]
        require(native_sole and vertices, "Missing foot-contact geometry")
        world_points = [
            (native.world[v["bone"]] @ np.r_[v["pos"], 1])[:3] for v in vertices
        ]
        sole = min(p[1] for p in world_points)
        target = min(native_sole)
        knee = native.world[knee_bone][1, 3]
        require(
            0.5 < (knee - target) / (knee - sole) < 2,
            "Unsupported foot-contact correction",
        )
        for vertex, point in zip(vertices, world_points):
            y, factor = ground_height(point[1], knee, sole, target)
            point[1] = y
            world = native.world[vertex["bone"]]
            vertex["pos"] = (np.linalg.inv(world) @ np.r_[point, 1])[:3]
            normal = np.linalg.inv(world[:3, :3]).T @ vertex["normal"]
            normal[1] /= factor
            normal = world[:3, :3].T @ normal
            vertex["normal"] = normal / max(float(np.linalg.norm(normal)), 1e-12)
        corrections.append(
            dict(foot=foot_bone, original_sole=float(sole), target_sole=float(target))
        )
    return corrections


def convert_actor(actor, model, *, age, entry=None):
    """Return a converted actor; callers activate it only after validation."""
    require(age in ("child", "adult"), "Choose child or adult")
    name, data, manifest = select(model, entry, age=age)
    limbs, order, slots = skeleton(data)
    writer = Writer(actor, age)
    m = writer.native
    ratios = []
    for child, parent in (
        (4, 3),
        (5, 4),
        (7, 6),
        (8, 7),
        (14, 13),
        (15, 14),
        (17, 16),
        (18, 17),
    ):
        length = np.linalg.norm(limbs[child]["position"])
        if length > 100:
            ratios.append(
                np.linalg.norm(
                    m.world[BONES[child]][:3, 3] - m.world[BONES[parent]][:3, 3]
                )
                / length
            )
    require(ratios, "Skeleton has no usable human joint lengths")
    scale = float(np.median(ratios))
    require(0.05 <= scale <= 10, "Unsupported skeleton scale")
    transforms = [np.eye(3) * scale for _ in limbs]
    for parent, child in (
        (3, 4),
        (4, 5),
        (6, 7),
        (7, 8),
        (13, 14),
        (14, 15),
        (16, 17),
        (17, 18),
        (20, 10),
        (12, 10),
    ):
        source = np.array(limbs[child]["position"], dtype=float)
        destination = (
            np.linalg.inv(m.world[BONES[parent]])
            @ np.r_[m.world[BONES[child]][:3, 3], 1]
        )[:3]
        length = float(np.linalg.norm(source))
        if length > 100 and np.linalg.norm(destination) > 100:
            axis = source / length
            stretch = np.eye(3) * scale + (
                np.linalg.norm(destination) / length - scale
            ) * np.outer(axis, axis)
            transforms[parent] = rotation(source, destination) @ stretch
    source = (
        np.array(limbs[2]["position"], dtype=float)
        + (np.array(limbs[3]["position"]) + np.array(limbs[6]["position"])) / 2
    )
    destination = (
        np.linalg.inv(m.world[2])
        @ np.r_[(m.world[3][:3, 3] + m.world[6][:3, 3]) / 2, 1]
    )[:3]
    if np.linalg.norm(source) > 100 and np.linalg.norm(destination) > 100:
        axis = source / np.linalg.norm(source)
        transforms[1] = rotation(source, destination) @ (
            np.eye(3) * scale
            + (np.linalg.norm(destination) / np.linalg.norm(source) - scale)
            * np.outer(axis, axis)
        )
    # Cap-local geometry follows the native cap joint, whose bind orientation
    # differs from the head. Treating long hair as rigid head geometry puts it
    # in front of the face.
    offsets = [np.zeros(3) for _ in limbs]
    # The native model has an extra chest joint. Borrow the closest native torso influence
    # so its chest animation does not pull the neck away from a rigid N64 torso.
    torso_points, torso_bones = [], []
    for mesh in m.meshes:
        if mesh[3] not in writer.body_groups:
            continue
        positions, _, _, indices, weights, primitives = m.geometry(H(mesh, 0))
        for _, _, mode, palette, used in primitives:
            for vi in np.unique(used):
                bone = palette[
                    0 if mode == 0 else indices[vi, int(np.argmax(weights[vi]))]
                ]
                if bone not in (2, 9, 10):
                    continue
                position = (
                    positions[vi]
                    if mode == 2
                    else (m.world[bone] @ np.r_[positions[vi], 1])[:3]
                )
                torso_points.append(position)
                torso_bones.append(bone)
    torso_points = np.array(torso_points)
    require(len(torso_points), "Native model has no torso deformation samples")
    segments = {6: data, 8: data, 9: data[0x4000:], 10: data}
    interpreter = Interp(segments)
    packets = collections.defaultdict(
        lambda: dict(vertices=[], triangles=[], tile=None)
    )
    total = 0
    for limb in order:
        if not limbs[limb]["dl"] or limb == 19:
            continue  # Preserve native equipment.
        for tri in interpreter.run_limb(limbs[limb]["dl"], slots.index(limb)):
            total += 1
            require(total <= 20000, "This model exceeds the 20,000-triangle import limit")
            tile = tri.tile
            state = tuple((k, getattr(tile, k)) for k in tile.__dataclass_fields__)
            packet = packets[(limb, state)]
            packet["tile"] = tile
            indices = []
            for v in tri.v:
                source = slots[v.flex_slot] if 0 <= v.flex_slot < len(slots) else limb
                require(
                    max(abs(v.x), abs(v.y), abs(v.z)) <= 16000, "Invalid model vertex"
                )
                if tile.lit:
                    normal = np.array(
                        [n - 256 if n > 127 else n for n in (v.r, v.g, v.b)],
                        dtype=float,
                    )
                    normal = np.linalg.inv(transforms[source]).T @ normal
                    normal /= max(float(np.linalg.norm(normal)), 1.0)
                    color = [1.0, 1.0, 1.0, v.a / 255.0]
                else:
                    normal = np.array([0.0, 1.0, 0.0])
                    color = [v.r / 255.0, v.g / 255.0, v.b / 255.0, v.a / 255.0]

                def shift(value, n):
                    return value / (1 << n) if n <= 10 else value * (1 << (16 - n))

                uv = [
                    (shift(v.s / 32.0, tile.shift_s) - tile.uls * 0.25)
                    / max(1, tile.width),
                    (shift(v.t / 32.0, tile.shift_t) - tile.ult * 0.25)
                    / max(1, tile.height),
                ]
                indices.append(len(packet["vertices"]))
                position = (
                    transforms[source] @ np.array([v.x, v.y, v.z]) + offsets[source]
                )
                bone = BONES[source]
                if source in (1, 12, 20):
                    world = (m.world[bone] @ np.r_[position, 1])[:3]
                    nearest = int(
                        np.argmin(np.sum((torso_points - world) ** 2, axis=1))
                    )
                    target = torso_bones[nearest]
                    correction = np.linalg.inv(m.world[target]) @ m.world[bone]
                    position = (correction @ np.r_[position, 1])[:3]
                    normal = correction[:3, :3] @ normal
                    bone = target
                packet["vertices"].append(
                    dict(
                        pos=position,
                        normal=normal,
                        color=color,
                        uv=uv,
                        bone=bone,
                    )
                )
            packet["triangles"].append(indices)
    require(total > 0, "No supported triangles found")
    ground_contact = fit_ground_contact(packets, m, writer.body_groups)
    for (limb, _), packet in packets.items():
        tile = packet["tile"]
        image = texture(segments, tile)
        material = writer.material(image, tile.cms, tile.cmt)
        groups = (
            sorted(writer.hand_groups["left" if limb == 15 else "right"])
            if limb in (15, 18)
            else writer.head_groups if limb in (10, 11, 12) else writer.body_groups
        )
        writer.append(packet["vertices"], packet["triangles"], material, groups)
    packed, cmb = writer.finish()
    report = dict(
        schema=1,
        age=age,
        entry=name,
        author=manifest.get("author", ""),
        source_name=manifest.get("name", Path(model).stem),
        source_form=data[0x500B],
        scale=scale,
        ground_contact=ground_contact,
        triangles=total,
        packets=len(packets),
        new_materials=len(writer.material_cache),
        actor_bytes=len(packed),
        native_equipment=True,
        native_skeleton=True,
    )
    return packed, report
