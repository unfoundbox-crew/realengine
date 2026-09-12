"""Blockout geometry: one named proxy volume per object in the build JSON.

The same thing the Three.js backend draws, so both backends render the same
scene from the same file. Deliberately dumb shapes -- position, size, colour
and name come from the spec; nothing is invented here.

``bpy`` is imported lazily inside the functions, so this module imports fine
on a machine with no Blender.
"""
from __future__ import annotations


def build_blockout(objects, collections=None, materials=None, scene=None):
    """Create one box per object spec. Requires Blender.

    Args:
        objects: list of dicts with ``name``, ``pos`` [x,y,z],
            ``size_m`` [w,d,h], optional ``collection`` and ``palette``.
        collections: {name: bpy collection} from ``ensure_collection_tree``.
        materials: {palette name: material} from ``build_material_table``.
        scene: target scene; defaults to the active one.

    Returns:
        {object name: object}
    """
    import bpy

    sc = scene or bpy.context.scene
    made = {}
    for spec in objects:
        mesh = bpy.data.meshes.new(spec["name"] + "_mesh")
        obj = bpy.data.objects.new(spec["name"], mesh)
        _unit_cube(mesh)
        obj.location = tuple(spec.get("pos", (0.0, 0.0, 0.0)))
        w, d, h = spec.get("size_m", (0.1, 0.1, 0.1))
        obj.scale = (w, d, h)

        target = None
        if collections:
            target = collections.get(spec.get("collection"))
        (target or sc.collection).objects.link(obj)

        if materials:
            mat = materials.get(spec.get("palette"))
            if mat is not None:
                obj.data.materials.append(mat)
        made[spec["name"]] = obj
    return made


def _unit_cube(mesh):
    """Fill ``mesh`` with a 1×1×1 cube centred on the origin. Requires Blender."""
    v = 0.5
    verts = [(-v, -v, -v), (v, -v, -v), (v, v, -v), (-v, v, -v),
             (-v, -v, v), (v, -v, v), (v, v, v), (-v, v, v)]
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
             (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return mesh
