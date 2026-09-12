"""Tessellate a compiled geometry part into verts/faces. No bpy, no numpy.

``spec/geometry.py`` emits primitives as numbers. The Three.js backend hands
those numbers to ``*Geometry`` constructors; Blender has no equivalent for a
lathe or a torus that works cleanly headless, so this module turns the same
numbers into raw ``(verts, faces)`` that ``mesh.from_pydata`` accepts.

Deliberately pure python: the tessellation is the part most likely to be wrong,
and keeping bpy out of it means the unit tests exercise it on a machine with no
Blender installed. Same convention as the compiler -- **Z up**, axial
primitives along **+Z**, torus in the **XY** plane, extrusion swept along +Z.
Quads throughout where quads are natural; Blender is happy with n-gons.
"""
from __future__ import annotations

import math

TAU = math.pi * 2.0


def part_mesh(part):
    """``(verts, faces)`` for one compiled part, in the part's own local frame.

    The part's ``pos`` and ``quat`` are the *object's* business -- they land on
    the Blender object transform, not baked into vertices, so the .blend stays
    editable by a human.
    """
    kind = part["kind"]
    builder = _BUILDERS.get(kind)
    if builder is None:
        raise ValueError("no tessellation for geometry kind %r" % kind)
    return builder(part)


def _cube(part):
    w, d, h = (c / 2.0 for c in part["size"])
    verts = [(-w, -d, -h), (w, -d, -h), (w, d, -h), (-w, d, -h),
             (-w, -d, h), (w, -d, h), (w, d, h), (-w, d, h)]
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
             (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return verts, faces


def _ring(radius, z, segments):
    return [(radius * math.cos(TAU * i / segments),
             radius * math.sin(TAU * i / segments), z)
            for i in range(segments)]


def _cylinder(part):
    """Cylinder, cone or truncated cone: one ring at each end plus caps."""
    n = int(part.get("segments", 32))
    half = part["height"] / 2.0
    r_bottom, r_top = part["radius_bottom"], part["radius_top"]
    verts, faces = [], []
    bottom = _ring(r_bottom, -half, n) if r_bottom > 0 else [(0.0, 0.0, -half)]
    top = _ring(r_top, half, n) if r_top > 0 else [(0.0, 0.0, half)]
    verts.extend(bottom)
    verts.extend(top)
    b0, t0 = 0, len(bottom)
    for i in range(n):
        j = (i + 1) % n
        if len(bottom) == 1:  # a true cone: triangles down to the apex
            faces.append((b0, t0 + j, t0 + i))
        elif len(top) == 1:
            faces.append((b0 + i, b0 + j, t0))
        else:
            faces.append((b0 + i, b0 + j, t0 + j, t0 + i))
    if len(bottom) > 1:
        faces.append(tuple(range(n - 1, -1, -1)))
    if len(top) > 1:
        faces.append(tuple(range(t0, t0 + n)))
    return verts, faces


def _sphere(part):
    """UV sphere: poles plus ``rings - 1`` latitude bands."""
    n = int(part.get("segments", 32))
    rings = max(2, int(part.get("rings", 16)))
    r = part["radius"]
    verts = [(0.0, 0.0, r)]
    for band in range(1, rings):
        phi = math.pi * band / rings
        verts.extend(_ring(r * math.sin(phi), r * math.cos(phi), n))
    verts.append((0.0, 0.0, -r))
    south = len(verts) - 1
    faces = []
    for i in range(n):
        faces.append((0, 1 + (i + 1) % n, 1 + i))
    for band in range(rings - 2):
        a, b = 1 + band * n, 1 + (band + 1) * n
        for i in range(n):
            j = (i + 1) % n
            faces.append((a + i, a + j, b + j, b + i))
    last = 1 + (rings - 2) * n
    for i in range(n):
        faces.append((south, last + i, last + (i + 1) % n))
    return verts, faces


def _torus(part):
    """Ring in the XY plane, tube swept around it."""
    n = int(part.get("segments", 32))
    m = max(3, int(part.get("tube_segments", 16)))
    big, tube = part["radius"], part["tube"]
    verts = []
    for i in range(n):
        a = TAU * i / n
        ca, sa = math.cos(a), math.sin(a)
        for j in range(m):
            b = TAU * j / m
            rr = big + tube * math.cos(b)
            verts.append((rr * ca, rr * sa, tube * math.sin(b)))
    faces = []
    for i in range(n):
        i2 = (i + 1) % n
        for j in range(m):
            j2 = (j + 1) % m
            faces.append((i * m + j, i2 * m + j, i2 * m + j2, i * m + j2))
    return verts, faces


def _lathe(part):
    """Revolve a ``[radius, z]`` profile around +Z."""
    profile = part["profile"]
    n = int(part.get("segments", 32))
    verts, faces = [], []
    for i in range(n):
        a = TAU * i / n
        ca, sa = math.cos(a), math.sin(a)
        for r, z in profile:
            verts.append((r * ca, r * sa, z))
    rows = len(profile)
    for i in range(n):
        i2 = (i + 1) % n
        for k in range(rows - 1):
            faces.append((i * rows + k, i * rows + k + 1,
                          i2 * rows + k + 1, i2 * rows + k))
    return verts, faces


def _extrude(part):
    """Sweep a closed 2D outline along +Z, capped at both ends."""
    outline = part["outline"]
    depth = part["depth"]
    n = len(outline)
    verts = [(x, y, 0.0) for x, y in outline]
    verts += [(x, y, depth) for x, y in outline]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return verts, faces


_BUILDERS = {
    "box": _cube,
    "cylinder": _cylinder,
    "cone": _cylinder,
    "sphere": _sphere,
    "torus": _torus,
    "lathe": _lathe,
    "extrude": _extrude,
}

KINDS = tuple(sorted(_BUILDERS))
