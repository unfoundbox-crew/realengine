---
name: code-to-3d-brain
description: Rebuild the academic human-brain predictive-control visualization in Blender from spec. Use when asked for the brain demo, anatomical reference scenes, or six-view QA rebuilds.
---

# Brain example (`examples/brain`)

Closed-loop neuro-cybernetic visualization: layered cortical lobes,
seven subcortical structures, 5-layer stack, control loop — six QA views.

## Run order (strict, one step at a time)

1. Read `SCENE_SPEC.md` — authoritative semantics, naming, dimensions.
   Priority: spec > orthographic refs > master view > styling.
2. Blender MCP server on `localhost:9876`, addon connected.
3. Execute `01_rebuild.py` … `11_final_adjustments.py` in order via
   `execute_blender_code` (see `mcp_call.py` for the call shape).
4. After each step, render its QA view (`render_views.py`, `02_preview.py`).
5. Never invent anatomy, labels, colors, or claims. Underspecified →
   simplest neutral implementation, logged as deviation.

## Done looks like

- `final/working.blend` + six QA PNGs matching `01_…png` … `06_…png`.
- `final/` previews; every named structure a separate object.
- Deviation log: spec wins conflicts explicitly, never silent blends.
