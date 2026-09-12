"""Three-point light rig + world background. Requires Blender (lazy bpy).

The pipeline used to build collections, materials and cameras and then save
a scene with no lights in it: every render came out black. This is the
missing piece, sized from the scene extent so it works at any scale.
"""
from __future__ import annotations


def hex_to_rgb(hex_color):
    """``#RRGGBB`` -> (r, g, b) floats. Pure python, no bpy."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def setup_world(scene, background="#F8FAFC", strength=1.0):
    """Flat studio background. Requires Blender."""
    import bpy

    world = bpy.data.worlds.new("CTD_World")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg is not None:
        bg.inputs["Color"].default_value = (*hex_to_rgb(background), 1.0)
        bg.inputs["Strength"].default_value = strength
    scene.world = world
    return world


def three_point(scene, extent=(1.0, 1.0, 1.0), center=(0.0, 0.0, 0.0),
                collection=None, energy_scale=1.0):
    """Key + fill + rim, placed relative to the scene extent. Requires Blender.

    Area-light power scales with distance squared, so a small metric scene
    and a large one both land at a sane exposure.
    """
    import bpy

    span = max(list(extent) + [0.001])
    dist = span * 3.0
    watts = 60.0 * energy_scale * (dist ** 2)
    rig = [
        ("LIGHT_Key", (-dist, -dist, dist * 1.1), watts, span * 2.5),
        ("LIGHT_Fill", (dist * 1.2, -dist * 0.6, dist * 0.5), watts * 0.35, span * 3.0),
        ("LIGHT_Rim", (0.0, dist * 1.2, dist * 0.9), watts * 0.25, span * 2.0),
    ]
    made = {}
    for name, pos, power, size in rig:
        data = bpy.data.lights.new(name, type="AREA")
        data.energy = power
        data.size = size
        obj = bpy.data.objects.new(name, data)
        obj.location = (center[0] + pos[0], center[1] + pos[1], center[2] + pos[2])
        _aim(obj, center)
        target = collection.get("10_LIGHTS") if isinstance(collection, dict) else collection
        (target or scene.collection).objects.link(obj)
        made[name] = obj
    return made


def _aim(obj, target):
    """Point ``obj``'s -Z at ``target``. Requires Blender."""
    from mathutils import Vector

    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat(
        "-Z", "Y").to_euler()
    return obj
