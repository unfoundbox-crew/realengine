"""Collection tree setup, generalized from 01_rebuild.py.

Seed logic: rename colliding top-level collections and matching objects
with a ``DRAFT_`` prefix (never delete), then create a fresh ordered set
of collections linked under the scene.
"""
from __future__ import annotations


def ensure_collection_tree(scene, names, rename_prefix="DRAFT_",
                           rename_objects_matching=()):
    """Create ``names`` as child collections of ``scene`` in order.

    Args:
        scene: a ``bpy.types.Scene`` (or anything exposing
            ``.collection`` for linking). ``bpy`` is imported lazily so
            this module stays import-safe without Blender.
        names: ordered collection names to create.
        rename_prefix: prefix applied to pre-existing colliding
            collections/objects instead of deleting them.
        rename_objects_matching: tuple of name prefixes; existing
            objects whose names start with any of them are renamed
            rather than removed.

    Returns:
        dict mapping each name in ``names`` to its collection.
    """
    import bpy

    for existing in list(bpy.data.collections):
        if existing.name in names:
            existing.name = rename_prefix + existing.name
    if rename_objects_matching:
        for obj in list(bpy.data.objects):
            if obj.name.startswith(rename_objects_matching):
                obj.name = rename_prefix + obj.name
    cols = {}
    for name in names:
        col = bpy.data.collections.new(name)
        scene.collection.children.link(col)
        cols[name] = col
    return cols


def get_collection_map(scene):
    """Return {name: collection} for a scene's direct children."""
    return {c.name: c for c in scene.collection.children}
