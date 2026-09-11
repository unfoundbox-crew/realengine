"""ctd_blender — spec-driven bpy helpers for code-to-3d.

All Blender interaction lives inside functions (lazy ``import bpy``), so
this package imports cleanly on machines without Blender.
"""
from .collections import ensure_collection_tree
from .materials import build_material_table, hex_to_linear, make_material
from .cameras import aim_camera, aim_cameras, create_camera
from .qa import collect_stats, render_view

__all__ = [
    "ensure_collection_tree",
    "build_material_table",
    "hex_to_linear",
    "make_material",
    "aim_camera",
    "aim_cameras",
    "create_camera",
    "collect_stats",
    "render_view",
]
