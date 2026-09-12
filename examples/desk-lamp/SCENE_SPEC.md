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

Every dimension is the object's axis-aligned bounding box. For an object with
modelled geometry the box is the bound of that geometry, not an invented
envelope -- `spec/geometry.py` warns if the two disagree by more than 1 mm.

- BNCH_Top: `1200 × 600 × 40 mm`
- LAMP_Base: `180 × 180 × 30 mm`
- LAMP_LowerArm: `55.8 × 36 × 264.3 mm`
- LAMP_UpperArm: `48.9 × 32 × 224 mm`
- LAMP_Shade: `140 × 140 × 120 mm`
- GLOW_Bulb: `60 × 60 × 60 mm`

## Geometry

Modelled geometry per object, in the object's own local frame, metres, Z up.
`BNCH_Top` is deliberately absent: a bench slab *is* a box, so it takes the
blockout fallback and `build.json` labels it `source: blockout`. The other five
are modelled -- a turned base, two jointed arms, a lathed shade, a spherical
bulb -- which is the whole point of the block.

```json
{
  "GLOW_Bulb": {
    "kind": "sphere",
    "radius": 0.03,
    "segments": 32,
    "rings": 16
  },
  "LAMP_Base": {
    "kind": "group",
    "parts": [
      { "kind": "cylinder", "radius": 0.09, "height": 0.022, "pos": [0, 0, -0.004], "segments": 48 },
      { "kind": "torus", "radius": 0.07, "tube": 0.008, "pos": [0, 0, 0.007], "segments": 48, "tube_segments": 16 }
    ]
  },
  "LAMP_LowerArm": {
    "kind": "arm",
    "joints": [[-0.012, 0, -0.13], [0.012, 0, 0.0], [-0.004, 0, 0.13]],
    "radius": 0.014,
    "joint_radius": 0.018,
    "caps": false,
    "segments": 20
  },
  "LAMP_Shade": {
    "kind": "lathe",
    "profile": [[0.012, -0.06], [0.016, -0.055], [0.068, 0.05], [0.07, 0.055], [0.07, 0.06]],
    "segments": 48
  },
  "LAMP_UpperArm": {
    "kind": "arm",
    "joints": [[0.0, 0, -0.11], [0.02, 0, 0.02], [0.006, 0, 0.11]],
    "radius": 0.013,
    "joint_radius": 0.016,
    "caps": false,
    "segments": 20
  }
}
```

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
