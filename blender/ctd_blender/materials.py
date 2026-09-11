"""Material table builder, from 01_rebuild.py + build_scene.py palettes.

01_rebuild.py builds Principled BSDF materials with sRGB->linear
conversion, recorded sRGB hex + alpha as custom props, and DITHERED
surface render for translucency. build_scene.py uses the same shape with
a simpler constructor. Both are covered here via parameters.
"""
from __future__ import annotations


def hex_to_linear(hex_color):
    """Convert ``#RRGGBB`` sRGB to linear-RGB tuple. Pure python, no bpy."""
    h = hex_color.lstrip("#")
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(
        x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
        for x in rgb
    )


def make_material(name, hex_color, alpha=1.0, roughness=0.45, prefix="MVEC_"):
    """Create one Principled BSDF material. Requires Blender (lazy bpy)."""
    import bpy

    mat = bpy.data.materials.new(prefix + name)
    mat.use_nodes = True
    principled = mat.node_tree.nodes.get("Principled BSDF")
    rgba = (*hex_to_linear(hex_color), alpha)
    if principled is not None:
        principled.inputs["Base Color"].default_value = rgba
        principled.inputs["Alpha"].default_value = alpha
        principled.inputs["Roughness"].default_value = roughness
    mat.diffuse_color = rgba
    mat["sRGB_hex"] = hex_color
    mat["specified_alpha"] = alpha
    if alpha < 1:
        mat.surface_render_method = "DITHERED"
    return mat


def build_material_table(palette, default_roughness=0.45, prefix="MVEC_"):
    """Build every material in ``palette``. Requires Blender (lazy bpy).

    Args:
        palette: mapping name -> spec, where spec is one of:
            - ``"#RRGGBB"`` (opaque, default roughness),
            - ``(hex, alpha)``,
            - ``(hex, alpha, roughness)``,
            - ``{"hex": ..., "alpha": ..., "roughness": ...}``.
        default_roughness: used when a spec omits roughness.
        prefix: prepended to each Blender material name.

    Returns:
        dict mapping each palette name to its material.
    """
    materials = {}
    for name, spec in palette.items():
        if isinstance(spec, str):
            hex_color, alpha, rough = spec, 1.0, default_roughness
        elif isinstance(spec, dict):
            hex_color = spec["hex"]
            alpha = spec.get("alpha", 1.0)
            rough = spec.get("roughness", default_roughness)
        else:
            hex_color = spec[0]
            alpha = spec[1] if len(spec) > 1 else 1.0
            rough = spec[2] if len(spec) > 2 else default_roughness
        materials[name] = make_material(name, hex_color, alpha, rough, prefix)
    return materials
