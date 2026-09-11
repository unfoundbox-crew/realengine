# Terra-Low Blender MCP Handoff

## Goal
Rebuild the academic human-brain predictive-control visualization in Blender, faithfully and deterministically.

## Inputs
- `SCENE_SPEC.md` — authoritative semantics, naming, dimensions, hierarchy, build order.
- `01_master_front.png`
- `02_left_orthographic.png`
- `03_top_orthographic.png`
- `04_detail_3q.png`
- `05_exploded_layers.png`
- `06_materials_dimensions.png`

## Priority
`SCENE_SPEC.md > orthographic views > perspective/master view > visual styling details`

## Instructions
1. Follow the build order in `SCENE_SPEC.md`.
2. Do not invent anatomy, labels, colors, dimensions, or extra scientific claims.
3. Use orthographic views to lock geometry and proportions before styling.
4. Keep every named structure as a separate object.
5. Match palette/material intent, not pixel-for-pixel lighting artifacts.
6. Render QA views from all six cameras before finalizing.
7. If references conflict, obey the priority rule above.
8. If something is underspecified, choose the simplest neutral implementation rather than guessing.
9. Do not ask for more input unless Blender/MCP itself is blocked.

## Deliverables
- `.blend` scene
- six QA renders matching the six references
- one final 16:9 master render
- short report listing any unavoidable deviations

## Acceptance
Pass only if:
- structure names match spec
- dimensions/proportions are within tolerance
- cortical/subcortical placement is coherent across all views
- labels do not overlap
- no decorative/non-academic styling is introduced
- scene remains editable/animation-ready
