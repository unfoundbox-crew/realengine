"""Object geometry: one named volume per object in the build JSON.

The same thing the Three.js backend draws, so both backends render the same
scene from the same file. Two levels, and the build JSON says which is which:

* ``geometry.source == "modelled"`` -- the spec gave this object a geometry
  block, so it gets real primitives: a turned base, a lathed shade, a jointed
  arm. One Blender object per part, parented to an empty named after the
  object, so a human opening the .blend still sees ``LAMP_Shade``.
* ``geometry.source == "blockout"``, or no ``geometry`` at all -- a proxy box
  scaled to ``size_m``. The historical path, unchanged, and never dressed up
  as modelled geometry.

Nothing is invented here: position, size, colour and name come from the spec.
``bpy`` is imported lazily inside the functions, so this module imports fine on
a machine with no Blender.
"""
from __future__ import annotations

from . import primitives


def build_blockout(objects, collections=None, materials=None, scene=None):
    """Create the geometry for every object spec. Requires Blender.

    Args:
        objects: list of dicts with ``name``, ``pos`` [x,y,z],
            ``size_m`` [w,d,h], optional ``collection``, ``palette`` and
            ``geometry`` (from ``spec/geometry.py``).
        collections: {name: bpy collection} from ``ensure_collection_tree``.
        materials: {palette name: material} from ``build_material_table``.
        scene: target scene; defaults to the active one.

    Returns:
        {object name: object} -- the named object, which is the mesh itself for
        a single-part object and an empty parenting the parts otherwise.
    """
    import bpy

    sc = scene or bpy.context.scene
    made = {}
    for spec in objects:
        target = None
        if collections:
            target = collections.get(spec.get("collection"))
        target = target or sc.collection
        mat = materials.get(spec.get("palette")) if materials else None

        geometry = spec.get("geometry") or {}
        parts = geometry.get("parts")
        if not parts:
            w, d, h = spec.get("size_m", (0.1, 0.1, 0.1))
            parts = [{"kind": "box", "size": [w, d, h],
                      "pos": [0.0, 0.0, 0.0], "quat": [0.0, 0.0, 0.0, 1.0]}]

        meshes = []
        for index, part in enumerate(parts):
            name = spec["name"] if len(parts) == 1 else "%s_%02d" % (spec["name"], index)
            verts, faces = primitives.part_mesh(part)
            mesh = bpy.data.meshes.new(name + "_mesh")
            mesh.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
            mesh.update()
            obj = bpy.data.objects.new(name, mesh)
            obj.location = tuple(part.get("pos", (0.0, 0.0, 0.0)))
            quat = part.get("quat") or (0.0, 0.0, 0.0, 1.0)
            obj.rotation_mode = "QUATERNION"
            # spec/geometry.py emits [x, y, z, w]; Blender wants (w, x, y, z).
            obj.rotation_quaternion = (quat[3], quat[0], quat[1], quat[2])
            target.objects.link(obj)
            if mat is not None:
                obj.data.materials.append(mat)
            meshes.append(obj)

        origin = tuple(spec.get("pos", (0.0, 0.0, 0.0)))
        if len(meshes) == 1:
            meshes[0].location = tuple(
                origin[i] + meshes[0].location[i] for i in range(3))
            made[spec["name"]] = meshes[0]
        else:
            holder = bpy.data.objects.new(spec["name"], None)
            holder.location = origin
            target.objects.link(holder)
            for obj in meshes:
                obj.parent = holder
            made[spec["name"]] = holder
    return made


def _unit_cube(mesh):
    """Fill ``mesh`` with a 1x1x1 cube centred on the origin. Requires Blender.

    Kept for callers that build a proxy volume by scaling an object, which is
    what this module did before it grew a primitive vocabulary.
    """
    v = 0.5
    verts = [(-v, -v, -v), (v, -v, -v), (v, v, -v), (-v, v, -v),
             (-v, -v, v), (v, -v, v), (v, v, v), (-v, v, v)]
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
             (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return mesh
