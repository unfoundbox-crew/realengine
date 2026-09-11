"""QA rendering + stats, from 03_check_render.py / render_views.py.

Seed logic: set ``scene.camera``, toggle per-camera overlay visibility
via the ``view`` custom prop, set resolution + filepath, render, and
report camera/collection state. All names and paths are parameters.
"""
from __future__ import annotations


def render_view(output_path, camera, scene=None, res_x=1600, res_y=1600,
                res_pct=100, samples=None, use_compositing=False):
    """Render one still from ``camera`` to ``output_path``. Needs Blender.

    Objects carrying a ``view`` custom prop are shown only when it
    matches the camera name (seed render_views.py behaviour).
    Returns the output path as a string.
    """
    import bpy

    sc = scene or bpy.context.scene
    cam_obj = bpy.data.objects[camera] if isinstance(camera, str) else camera
    sc.camera = cam_obj
    for obj in sc.objects:
        view = obj.get("view")
        if view:
            obj.hide_render = view != cam_obj.name
    sc.render.resolution_x = res_x
    sc.render.resolution_y = res_y
    sc.render.resolution_percentage = res_pct
    sc.render.use_compositing = use_compositing
    if samples is not None and hasattr(sc.cycles, "samples"):
        sc.cycles.samples = samples
    sc.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True, scene=sc.name)
    return str(output_path)


def collect_stats(scene=None):
    """Snapshot camera/collection/render state. Needs Blender.

    Mirrors the 03_check_render.py prints, returned as a dict instead.
    """
    import bpy

    sc = scene or bpy.context.scene
    cam = sc.camera
    return {
        "camera": {
            "name": cam.name if cam else None,
            "location": list(cam.location) if cam else None,
            "rotation_euler": list(cam.rotation_euler) if cam else None,
        },
        "collections": [
            {"name": c.name, "hide_render": c.hide_render}
            for c in sc.collection.children
        ],
        "render": {
            "engine": sc.render.engine,
            "res_x": sc.render.resolution_x,
            "res_y": sc.render.resolution_y,
            "res_pct": sc.render.resolution_percentage,
            "filepath": sc.render.filepath,
        },
        "objects": len(sc.objects),
    }
