# Desk Lamp Scene Spec

A hand-written second example: a jointed desk lamp on a bench. It exists to
prove the pipeline is not brain-shaped — same parser, same build JSON, same
backends, a completely different subject.

## Units and coordinates

- Metric units; 1 unit = 1 meter
- Z up, X left/right, Y depth
- Bench envelope: `1.200 × 0.600 × 0.040 m`
- Lamp envelope: `0.180 × 0.180 × 0.520 m`
- Placement tolerance: major forms ±5 mm

## Palette

- Base `#3F4A57` alpha 1 roughness 0.5
- Arm `#8C97A3` alpha 1 roughness 0.35
- Shade `#E4B363` alpha 1 roughness 0.4
- Bulb `#FFF3D6` alpha 0.9 roughness 0.1
- Bench `#C9A227` alpha 1 roughness 0.7

## Collections

```text
SCENE
├── 00_REFERENCE
├── 01_BENCH
├── 02_LAMP
├── 03_LIGHTING
├── 07_LABELS
├── 09_CAMERAS
└── 10_LIGHTS
```

## Naming

Prefix to collection:

```text
BNCH_ -> 01_BENCH
LAMP_ -> 02_LAMP
GLOW_ -> 03_LIGHTING
```

Required objects:

```text
BNCH_Top
LAMP_Base
LAMP_LowerArm
LAMP_UpperArm
LAMP_Shade
GLOW_Bulb
```

## Object dimensions

- BNCH_Top: `1200 × 600 × 40 mm`
- LAMP_Base: `180 × 180 × 30 mm`
- LAMP_LowerArm: `40 × 40 × 260 mm`
- LAMP_UpperArm: `36 × 36 × 220 mm`
- LAMP_Shade: `140 × 140 × 120 mm`
- GLOW_Bulb: `60 × 60 × 60 mm`

## Cameras

- `CAM_Master` — 3/4 overview of the bench, 16:9
- `CAM_LeftOrthographic` — side elevation, joint angles readable
- `CAM_FrontOrthographic` — front elevation
- `CAM_Detail` — close on the shade and bulb

## Functional labels

- Base — Weighted foot, holds the arm upright
- LowerArm — First link, sprung
- UpperArm — Second link, carries the shade
- Shade — Cone that aims the light down
- Bulb — Emitter
- Top — Bench surface

## Render

- master `1600×900`
- orthographic refs `1200×1200`
- engine Eevee

## Lighting

Background `#F4F6F8`; large soft key, soft fill, no bloom or volumetrics.

## Deterministic build order

```text
01 collections
02 bench top
03 lamp base
04 lower arm
05 upper arm
06 shade
07 bulb
08 materials
09 labels
10 cameras
11 lights
12 orthographic QA renders
13 master render
```

## Priority

Conflict priority: `scene_spec.md > orthographic views > master perspective > detail aesthetics`
