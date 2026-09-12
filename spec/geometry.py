#!/usr/bin/env python3
"""Geometry compiler: an object's ``geometry`` block -> flat primitive parts.

Why this exists
---------------
Until now every object in every scene was a box. ``blockout.py`` made one unit
cube per object and the Three.js template drew one ``BoxGeometry`` per object,
so a desk lamp and a brain rendered as the same pile of rectangles. The
blockout is a *stage*, not the product.

This module is the stage after it. A spec may give any object an optional
``geometry`` block; this compiler turns that block into a flat list of
primitive parts in the object's local frame. The parts are plain data --
numbers, no library types -- so both backends stay dumb: the Three.js template
maps one part to one ``*Geometry``, and Blender maps one part to one mesh.

Everything here is pure, deterministic and stdlib-only. Same input bytes,
same output numbers, on any machine.

Conventions (normative)
-----------------------
* **Z up**, metres, matching ``SCENE_SPEC.md``. Every axial primitive
  (cylinder, cone, lathe) runs along **+Z**; a torus lies in the **XY** plane;
  an extrusion is swept along **+Z**. A Y-up renderer rotates at draw time --
  that is the renderer's problem, not the spec's.
* Rotation leaves this module as a **quaternion** ``[x, y, z, w]``, never
  Euler angles: quaternions compose without an order convention to argue
  about, and both Three.js and Blender accept them directly. A block may be
  *authored* with ``rot_deg: [rx, ry, rz]`` (intrinsic X, then Y, then Z),
  which is converted here.
* A ``group`` node carries **translation only**. Rotating a group would need
  a full transform stack; a leaf part carries its own rotation instead. A
  rotation on a group is an error, not a silent drop.
* Nothing is rescaled to fit the spec's ``size_mm``. The spec is the contract:
  if the modelled parts disagree with the declared envelope by more than
  ``FIT_TOLERANCE_M``, the compiler says so in ``warnings`` and the build
  carries the warning. Silent rescaling would make the dimensions a lie.

Public API
----------
``compile_object_geometry(block, size_m) -> dict``
    ``{"source": "modelled"|"blockout", "kind": str, "parts": [...],
       "aabb": [[x0,y0,z0],[x1,y1,z1]], "warnings": [str, ...]}``
    ``block=None`` yields the blockout fallback: one box the size of
    ``size_m``, ``source="blockout"``. The fallback is labelled, never
    disguised as modelled geometry.

``part_aabb(part)``, ``union_aabb(parts)``, ``aabbs_overlap(a, b, tol)``
    The overlap primitives ``qa/asserts.no_overlap`` is built on.
"""
from __future__ import annotations

import math

GEOMETRY_MODULE_VERSION = "0.1.0"

# Primitive vocabulary. "group" and "arm" are composites: they compile away.
LEAF_KINDS = ("box", "cylinder", "cone", "sphere", "torus", "lathe", "extrude")
COMPOSITE_KINDS = ("group", "arm")
KINDS = LEAF_KINDS + COMPOSITE_KINDS

# Dimension disagreement we are willing to call a rounding artefact.
FIT_TOLERANCE_M = 0.001

IDENTITY_QUAT = (0.0, 0.0, 0.0, 1.0)
DEFAULT_SEGMENTS = 32


class GeometryError(ValueError):
    """A geometry block that cannot be compiled. Fail closed, name the field."""


# ------------------------------------------------------------------ numbers


def _round(x, nd=6):
    """Round for JSON stability: -0.0 and 1e-17 must not reach the file."""
    v = round(float(x), nd)
    return 0.0 if v == 0 else v


def _vec3(value, field, default=(0.0, 0.0, 0.0)):
    if value is None:
        return tuple(float(c) for c in default)
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise GeometryError("%s must be three numbers, got %r" % (field, value))
    try:
        return tuple(float(c) for c in value)
    except (TypeError, ValueError):
        raise GeometryError("%s must be three numbers, got %r" % (field, value))


def _num(block, key, default=None, positive=True):
    if key not in block or block[key] is None:
        if default is None:
            raise GeometryError("%s needs %r" % (block.get("kind", "part"), key))
        return float(default)
    try:
        v = float(block[key])
    except (TypeError, ValueError):
        raise GeometryError("%s.%s must be a number, got %r"
                            % (block.get("kind", "part"), key, block[key]))
    if positive and v <= 0:
        raise GeometryError("%s.%s must be > 0, got %r"
                            % (block.get("kind", "part"), key, v))
    return v


def _segments(block, key="segments", default=DEFAULT_SEGMENTS):
    n = int(block.get(key, default) or default)
    if n < 3:
        raise GeometryError("%s must be >= 3, got %d" % (key, n))
    return n


def quat_from_euler_deg(rx, ry, rz):
    """Intrinsic X-then-Y-then-Z degrees -> quaternion ``[x, y, z, w]``."""
    hx, hy, hz = (math.radians(a) / 2.0 for a in (rx, ry, rz))
    cx, sx = math.cos(hx), math.sin(hx)
    cy, sy = math.cos(hy), math.sin(hy)
    cz, sz = math.cos(hz), math.sin(hz)
    return (
        sx * cy * cz + cx * sy * sz,
        cx * sy * cz - sx * cy * sz,
        cx * cy * sz + sx * sy * cz,
        cx * cy * cz - sx * sy * sz,
    )


def quat_z_to(direction):
    """Shortest-arc quaternion taking **+Z** onto ``direction``.

    This is how a parametric arm aims its links: every cylinder is authored
    along +Z and then rotated onto the joint-to-joint vector.
    """
    x, y, z = direction
    length = math.sqrt(x * x + y * y + z * z)
    if length == 0:
        raise GeometryError("cannot aim at a zero-length direction")
    x, y, z = x / length, y / length, z / length
    dot = z  # (0,0,1) . (x,y,z)
    if dot >= 1.0 - 1e-12:
        return IDENTITY_QUAT
    if dot <= -1.0 + 1e-12:
        return (1.0, 0.0, 0.0, 0.0)  # 180 deg about X
    # axis = Zx d, then half-angle form
    ax, ay, az = -y, x, 0.0
    w = 1.0 + dot
    n = math.sqrt(ax * ax + ay * ay + az * az + w * w)
    return (ax / n, ay / n, az / n, w / n)


def quat_rotate(quat, point):
    """Rotate ``point`` by ``quat`` ([x, y, z, w]). Pure python."""
    qx, qy, qz, qw = quat
    px, py, pz = point
    # t = 2 * (q_vec x p)
    tx = 2.0 * (qy * pz - qz * py)
    ty = 2.0 * (qz * px - qx * pz)
    tz = 2.0 * (qx * py - qy * px)
    return (
        px + qw * tx + (qy * tz - qz * ty),
        py + qw * ty + (qz * tx - qx * tz),
        pz + qw * tz + (qx * ty - qy * tx),
    )


# ------------------------------------------------------------------- bounds


def _half_extent(part):
    """Half-extent of a part's *unrotated* bounds, about its own origin."""
    kind = part["kind"]
    if kind == "box":
        w, d, h = part["size"]
        return (w / 2.0, d / 2.0, h / 2.0)
    if kind in ("cylinder", "cone"):
        r = max(part["radius_bottom"], part["radius_top"])
        return (r, r, part["height"] / 2.0)
    if kind == "sphere":
        r = part["radius"]
        return (r, r, r)
    if kind == "torus":
        outer = part["radius"] + part["tube"]
        return (outer, outer, part["tube"])
    if kind == "lathe":
        radii = [abs(p[0]) for p in part["profile"]]
        zs = [p[1] for p in part["profile"]]
        r = max(radii)
        return (r, r, (max(zs) - min(zs)) / 2.0)
    if kind == "extrude":
        xs = [p[0] for p in part["outline"]]
        ys = [p[1] for p in part["outline"]]
        return (max(abs(min(xs)), abs(max(xs))), max(abs(min(ys)), abs(max(ys))),
                part["depth"] / 2.0)
    raise GeometryError("no bounds rule for kind %r" % kind)


def _unrotated_center(part):
    """Some primitives are not centred on their own origin."""
    kind = part["kind"]
    if kind == "lathe":
        zs = [p[1] for p in part["profile"]]
        return (0.0, 0.0, (max(zs) + min(zs)) / 2.0)
    if kind == "extrude":
        xs = [p[0] for p in part["outline"]]
        ys = [p[1] for p in part["outline"]]
        return ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0,
                part["depth"] / 2.0)
    return (0.0, 0.0, 0.0)


# Primitives that are a solid of revolution about their own +Z: their exact
# rotated bounds are cheap, and a corner box would be far too loose for a
# diagonal arm link -- which is exactly where the overlap gate has to be sharp.
_AXIAL_KINDS = ("cylinder", "cone", "lathe")


def _axial_aabb(part):
    """Exact AABB of a rotated solid of revolution about +Z.

    For a body of radius ``r`` and half-height ``hz`` whose axis is the unit
    vector ``d``, the extent along world axis ``i`` is
    ``|d_i| * hz + r * sqrt(1 - d_i**2)`` -- the axis term plus the widest
    slice of the circular cross-section projected onto that axis.
    """
    hx, _hy, hz = _half_extent(part)
    r = hx
    quat = tuple(part.get("quat", IDENTITY_QUAT))
    pos = tuple(part.get("pos", (0.0, 0.0, 0.0)))
    axis = quat_rotate(quat, (0.0, 0.0, 1.0))
    center = quat_rotate(quat, _unrotated_center(part))
    lo, hi = [0.0] * 3, [0.0] * 3
    for i in range(3):
        d = max(-1.0, min(1.0, axis[i]))
        reach = abs(d) * hz + r * math.sqrt(max(0.0, 1.0 - d * d))
        mid = center[i] + pos[i]
        lo[i], hi[i] = mid - reach, mid + reach
    return [[_round(v) for v in lo], [_round(v) for v in hi]]


def part_aabb(part):
    """Axis-aligned bounds of one compiled part, in the object's local frame.

    Exact for a sphere and for any solid of revolution; a rotated box gets the
    bounds of its rotated corner box, which for a box is also exact. Bounds
    are per *part*, never one union box per object -- a union box around a
    jointed arm would fail the overlap gate on thin air.
    """
    if part["kind"] in _AXIAL_KINDS:
        return _axial_aabb(part)
    hx, hy, hz = _half_extent(part)
    cx, cy, cz = _unrotated_center(part)
    quat = tuple(part.get("quat", IDENTITY_QUAT))
    pos = tuple(part.get("pos", (0.0, 0.0, 0.0)))
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                corner = (cx + sx * hx, cy + sy * hy, cz + sz * hz)
                rx, ry, rz = quat_rotate(quat, corner)
                for i, v in enumerate((rx + pos[0], ry + pos[1], rz + pos[2])):
                    lo[i] = min(lo[i], v)
                    hi[i] = max(hi[i], v)
    return [[_round(v) for v in lo], [_round(v) for v in hi]]


def union_aabb(parts):
    """Union of every part's AABB, or ``None`` for no parts."""
    boxes = [part_aabb(p) for p in parts]
    if not boxes:
        return None
    lo = [min(b[0][i] for b in boxes) for i in range(3)]
    hi = [max(b[1][i] for b in boxes) for i in range(3)]
    return [[_round(v) for v in lo], [_round(v) for v in hi]]


def aabbs_overlap(a, b, tol=0.0):
    """True iff two AABBs interpenetrate by more than ``tol`` on every axis.

    ``tol`` is slack, not margin: a positive tolerance lets touching or
    slightly-interpenetrating parts pass, which is what a placement tolerance
    of +/-5 mm means in practice.
    """
    for i in range(3):
        if a[1][i] - tol <= b[0][i] or b[1][i] - tol <= a[0][i]:
            return False
    return True


def overlap_depth(a, b):
    """Per-axis interpenetration of two AABBs; negative means separated."""
    return [_round(min(a[1][i], b[1][i]) - max(a[0][i], b[0][i])) for i in range(3)]


# ------------------------------------------------------------------ compile


def _leaf(kind, block, offset, quat):
    """Compile one leaf primitive into normal form."""
    part = {"kind": kind,
            "pos": [_round(c) for c in offset],
            "quat": [_round(c) for c in quat]}
    if kind == "box":
        part["size"] = [_round(c) for c in _vec3(block.get("size"), "box.size",
                                                 (0.05, 0.05, 0.05))]
    elif kind == "cylinder":
        r = _num(block, "radius", block.get("radius_bottom", 0.02))
        part["radius_bottom"] = _round(_num(block, "radius_bottom", r))
        part["radius_top"] = _round(_num(block, "radius_top", r, positive=False))
        part["height"] = _round(_num(block, "height"))
        part["segments"] = _segments(block)
    elif kind == "cone":
        part["radius_bottom"] = _round(_num(block, "radius"))
        part["radius_top"] = _round(_num(block, "radius_top", 0.0, positive=False))
        part["height"] = _round(_num(block, "height"))
        part["segments"] = _segments(block)
    elif kind == "sphere":
        part["radius"] = _round(_num(block, "radius"))
        part["segments"] = _segments(block)
        part["rings"] = _segments(block, "rings", max(3, DEFAULT_SEGMENTS // 2))
    elif kind == "torus":
        part["radius"] = _round(_num(block, "radius"))
        part["tube"] = _round(_num(block, "tube"))
        part["segments"] = _segments(block)
        part["tube_segments"] = _segments(block, "tube_segments", 16)
    elif kind == "lathe":
        part["profile"] = _profile(block.get("profile"), "lathe.profile")
        part["segments"] = _segments(block)
    elif kind == "extrude":
        part["outline"] = _profile(block.get("outline"), "extrude.outline",
                                   minimum=3)
        part["depth"] = _round(_num(block, "depth"))
    else:  # pragma: no cover - guarded by the caller
        raise GeometryError("unknown leaf kind %r" % kind)
    return part


def _profile(points, field, minimum=2):
    if not isinstance(points, (list, tuple)) or len(points) < minimum:
        raise GeometryError("%s needs at least %d [u, v] points, got %r"
                            % (field, minimum, points))
    out = []
    for p in points:
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            raise GeometryError("%s point must be [u, v], got %r" % (field, p))
        out.append([_round(float(p[0])), _round(float(p[1]))])
    return out


def _quat_of(block, field):
    if "quat" in block and block["quat"] is not None:
        q = block["quat"]
        if not isinstance(q, (list, tuple)) or len(q) != 4:
            raise GeometryError("%s.quat must be four numbers, got %r" % (field, q))
        n = math.sqrt(sum(float(c) ** 2 for c in q)) or 1.0
        return tuple(float(c) / n for c in q)
    if "rot_deg" in block and block["rot_deg"] is not None:
        return quat_from_euler_deg(*_vec3(block["rot_deg"], "%s.rot_deg" % field))
    return IDENTITY_QUAT


def _compile_arm(block, offset):
    """Parametric arm: a joint polyline becomes links plus joint balls.

    A jointed lamp arm is the one shape a box vocabulary cannot fake. Author
    the joints, get a chain: one capsule-ish cylinder per segment aimed along
    the segment, one sphere at each joint so the elbows read as elbows.
    """
    joints = block.get("joints")
    if not isinstance(joints, (list, tuple)) or len(joints) < 2:
        raise GeometryError("arm.joints needs at least two [x, y, z] points")
    pts = [_vec3(j, "arm.joints[]") for j in joints]
    radius = _num(block, "radius", 0.018)
    joint_radius = _num(block, "joint_radius", radius * 1.25)
    segments = _segments(block, default=16)
    caps = bool(block.get("caps", True))

    parts = []
    for a, b in zip(pts, pts[1:]):
        direction = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        length = math.sqrt(sum(c * c for c in direction))
        if length <= 0:
            raise GeometryError("arm.joints has a zero-length segment")
        mid = tuple((a[i] + b[i]) / 2.0 + offset[i] for i in range(3))
        parts.append(_leaf("cylinder",
                           {"radius": radius, "height": length,
                            "segments": segments},
                           mid, quat_z_to(direction)))
    ball_at = pts if caps else pts[1:-1]
    for p in ball_at:
        parts.append(_leaf("sphere",
                           {"radius": joint_radius, "segments": segments,
                            "rings": max(3, segments // 2)},
                           tuple(p[i] + offset[i] for i in range(3)),
                           IDENTITY_QUAT))
    return parts


def _compile_node(block, offset, path="geometry"):
    """Recursively compile one node into a flat list of leaf parts."""
    if not isinstance(block, dict):
        raise GeometryError("%s must be an object, got %r" % (path, block))
    kind = block.get("kind")
    if kind not in KINDS:
        raise GeometryError("%s.kind must be one of %s, got %r"
                            % (path, ", ".join(KINDS), kind))
    local = _vec3(block.get("pos"), "%s.pos" % path)
    here = tuple(offset[i] + local[i] for i in range(3))

    if kind == "group":
        if block.get("rot_deg") or block.get("quat"):
            raise GeometryError(
                "%s: a group carries translation only -- put the rotation on "
                "the leaf parts" % path)
        children = block.get("parts")
        if not isinstance(children, (list, tuple)) or not children:
            raise GeometryError("%s.parts must be a non-empty list" % path)
        parts = []
        for i, child in enumerate(children):
            parts.extend(_compile_node(child, here, "%s.parts[%d]" % (path, i)))
        return parts
    if kind == "arm":
        return _compile_arm(block, here)
    return [_leaf(kind, block, here, _quat_of(block, path))]


def blockout_parts(size_m):
    """The fallback: one box the size of the declared envelope."""
    w, d, h = (max(float(c), 0.001) for c in size_m)
    return [{"kind": "box", "size": [_round(w), _round(d), _round(h)],
             "pos": [0.0, 0.0, 0.0], "quat": list(IDENTITY_QUAT)}]


def compile_object_geometry(block, size_m):
    """Compile one object's geometry block; ``None`` -> the blockout fallback.

    The result always names its ``source``. A reader of ``build.json`` can
    always tell modelled geometry from a proxy box -- that distinction is the
    whole point of the field.
    """
    if block is None:
        parts = blockout_parts(size_m)
        return {"source": "blockout", "kind": "box", "parts": parts,
                "aabb": union_aabb(parts), "warnings": []}

    parts = _compile_node(block, (0.0, 0.0, 0.0))
    aabb = union_aabb(parts)
    warnings = []
    if aabb is not None and size_m:
        axes = ("x", "y", "z")
        for i in range(3):
            modelled = aabb[1][i] - aabb[0][i]
            declared = float(size_m[i])
            if abs(modelled - declared) > FIT_TOLERANCE_M:
                warnings.append(
                    "%s extent %.4f m differs from the spec's %.4f m "
                    "(nothing was rescaled; fix the spec or the geometry)"
                    % (axes[i], modelled, declared))
    return {"source": "modelled", "kind": block.get("kind"), "parts": parts,
            "aabb": aabb, "warnings": warnings}


def object_world_boxes(obj):
    """World-space AABBs of one built object's parts, for the overlap gate.

    Accepts an entry from ``build.json``'s ``objects``: its ``pos`` is the
    object origin, its ``geometry.parts`` (or its ``size_m`` box, when the
    object predates geometry) are local to that origin.
    """
    pos = _vec3(obj.get("pos"), "object.pos")
    geometry = obj.get("geometry")
    parts = (geometry or {}).get("parts")
    if not parts:
        parts = blockout_parts(obj.get("size_m", (0.1, 0.1, 0.1)))
    boxes = []
    for part in parts:
        lo, hi = part_aabb(part)
        boxes.append([[_round(lo[i] + pos[i]) for i in range(3)],
                      [_round(hi[i] + pos[i]) for i in range(3)]])
    return boxes
