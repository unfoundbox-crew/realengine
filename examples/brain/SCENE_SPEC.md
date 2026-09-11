# Human Brain Predictive-Control Scene Spec

Version: 0.1  
Target: Blender + MCP  
Purpose: deterministic reconstruction of the academic brain infographic with minimal agent interpretation.

## Scene goal
Create a clean academic 3D visualization of the human brain as a layered predictive-control system.

Primary flow:
`Perceive → Encode → Predict → Compare → Update → Plan/Decide → Act → Environment feedback`

Language is a high-level interface, not the base layer.

## Units and coordinates
- Metric units; 1 Blender unit = 1 meter
- Z up, X left/right, Y depth
- Face points toward `-Y`
- Brain envelope: `0.150 × 0.175 × 0.135 m`
- Head envelope: `0.175 × 0.215 × 0.240 m`
- Placement tolerance: major forms ±3 mm; labels/arrows ±5 mm

## Collections
```text
SCENE
├── 00_REFERENCE
├── 01_HEAD
├── 02_BRAIN_CORTEX
├── 03_SUBCORTICAL
├── 04_FLOW_ARROWS
├── 05_LAYER_STACK
├── 06_CONTROL_LOOP
├── 07_LABELS
├── 08_LEGENDS
├── 09_CAMERAS
└── 10_LIGHTS
```

## Naming
Prefixes:
`HEAD_ CTX_ SUB_ FLOW_ LAYER_ CTRL_ LABEL_ LEGEND_ CAM_ LIGHT_`

Required:
`CTX_Frontal CTX_Parietal CTX_Temporal CTX_Occipital`
`SUB_Thalamus SUB_Hippocampus SUB_Amygdala SUB_BasalGanglia SUB_Cerebellum SUB_Brainstem SUB_ACC`

## Head
Simplified translucent lateral head shell.
- neutral adult proportions
- no hair, photoreal skin, or decorative detail
- alpha `0.08–0.12`
- material: `#E8EEF3`, roughness `0.55`

## Cortical regions
Required:
- Frontal cortex
- Parietal cortex
- Temporal cortex
- Occipital cortex

Palette:
- Frontal `#7EA6FF`
- Parietal `#82D6A4`
- Temporal `#F0C96C`
- Occipital `#A989D8`

Alpha `0.52–0.62`; roughness `0.45`; no emission.

## Subcortical structures
Simplified smooth volumes, not medical-grade anatomy.

- Thalamus: central ellipse, cyan, ~`35×28×25 mm`
- Hippocampus: inferior-medial temporal, curved, teal, ~`40 mm` long
- Amygdala: anterior to hippocampus, green, ~`14 mm`
- Basal ganglia: anterior-central cluster, coral, ~`28 mm`
- Cerebellum: posterior-inferior, orange, ~`50×30×35 mm`
- Brainstem: inferior central stalk, gray, ~`20×18×45 mm`
- ACC: curved band, muted red/pink

## Functional labels
Use exact names plus short subtitles:
- Prefrontal Cortex — Planning, decision making, abstraction, goal management
- Parietal Cortex — Spatial representation, attention, sensorimotor integration
- Temporal Cortex — Object recognition, semantic memory, language comprehension
- Occipital Cortex — Visual processing
- Anterior Cingulate Cortex — Error monitoring, conflict detection, attention control
- Basal Ganglia — Action selection, habit learning, reward processing
- Thalamus — Sensory relay and information routing
- Hippocampus — Memory formation and spatial navigation
- Amygdala — Emotion, salience, threat detection
- Cerebellum — Motor control, prediction error correction, timing
- Brainstem — Vital functions, arousal, neuromodulation

Typography: clean sans-serif; labels always camera-facing.

## Prediction/action loop
```text
Perceive
↓
Encode
↓
Predict
↓
Compare
↓
Update
↓
Plan & Decide
↓
Act
↓
Environment
↺ feedback to Perceive
```

Use flat rounded cards, white fill, dark border, `2–4 mm` depth.

Primary arrows:
- solid dark curves
- consistent arrowheads
- no glow

Modulatory arrows:
- memory, emotion, attention, goals/values
- thinner and dashed
- max 10 major arrows

## Layered processing stack
Five translucent horizontal layers:
```text
L5 Language & Social Cognition
L4 Abstract Reasoning & Planning
L3 World Model / Internal Simulation
L2 Perception & Representation
L1 Sensorimotor & Homeostasis
```

Per layer:
- width `120 mm`
- depth `50 mm`
- thickness `4 mm`
- vertical gap `14 mm`
- 5–9 sparse nodes with thin links

Colors:
- L5 `#A989D8`
- L4 `#7EA6FF`
- L3 `#82D6A4`
- L2 `#F0C96C`
- L1 `#E58982`

## Closed-loop control diagram
```text
Environment
→ Perception
→ Internal Model
→ Comparison
→ Update
→ Decision
→ Action
→ Environment
```
Add feedback `Environment → Perception`.

## Principles panel
1. Predictive — anticipates possible future states.
2. Adaptive — updates internal models from prediction error.
3. Multi-modal — combines sensory and internal signals.
4. Hierarchical — operates across abstraction levels and timescales.
5. Embodied — grounded in a body interacting with an environment.
6. Goal-directed — shaped by needs, values, and context.

## Cameras
Create exactly six:
- `CAM_Master` — 3/4 overview, 16:9
- `CAM_LeftOrthographic`
- `CAM_FrontOrthographic`
- `CAM_TopOrthographic`
- `CAM_ExplodedLayers`
- `CAM_Detail`

Perspective lenses: 55–70 mm equivalent.

## Lighting
Academic product-visualization lighting:
- large soft key
- soft fill
- optional weak rim
- white / `#F8FAFC` background
- no bloom, volumetrics, neon, or dramatic contrast

## Render
- Cycles final; Eevee preview acceptable
- master `2048×1152`
- orthographic refs `1600×1600`
- AgX, neutral
- subtle AO

## Animation readiness
- arrows must remain curves with stable spline direction
- regions stay separate named objects
- do not destructively join
- support later signal pulses, region highlights, loop activation, layer-to-layer flow

## Deterministic build order
```text
01 scene units / collections
02 head envelope
03 brain base
04 cortical regions
05 subcortical volumes
06 materials
07 prediction/action cards
08 primary arrows
09 modulatory arrows
10 layered-processing stack
11 control-loop diagram
12 legend panels
13 labels
14 six cameras
15 lights
16 dimension validation
17 naming validation
18 orthographic QA renders
19 fix overlaps
20 master render
```

## Agent constraints
Do NOT:
- invent extra brain regions or scientific claims
- add particles, glow, neon, photoreal skin
- merge named anatomical objects
- use random placement
- change palette or exact label text
- use perspective cameras for orthographic QA

If information is missing: preserve geometry, choose the simplest neutral implementation, and do not invent scientific meaning.

## Acceptance checklist
- four cortical regions readable
- all seven named subcortical structures present
- prediction/action loop obvious
- modulatory arrows visually distinct
- five processing layers present
- labels readable without overlap
- academic white-paper aesthetic
- six cameras correctly named
- naming convention followed
- scene remains animation-ready

## Six-image reference set
```text
01_master.png
02_left_ortho.png
03_front_ortho.png
04_top_ortho.png
05_exploded_layers.png
06_detail_materials_labels.png
```

Conflict priority:
`scene_spec.md > orthographic views > master perspective > detail aesthetics`

This file is authoritative for semantics, naming, dimensions, hierarchy, and build order.
