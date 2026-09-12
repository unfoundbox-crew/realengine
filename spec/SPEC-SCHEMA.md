# SCENE_SPEC.md — Schema (v0.2.0)

The machine-checkable shape of a code-to-3d scene spec.
A spec is one Markdown file, `SCENE_SPEC.md`, human-readable first.

## Required sections (validator-enforced)

| # | Section (heading match, case-insensitive) | Contents |
|---|---|---|
| 1 | `Units` (`## Units…`) | units, axis convention, envelopes, tolerances |
| 2 | `Palette` (any `palette` line) | named hex colors per region/layer |
| 3 | `Collections` (`## Collections`) | `SCENE` tree in a fenced block |
| 4 | `Cameras` (`## Cameras`) | ≥1 `CAM_<Name>` entries |
| 5 | `Build order` (`## …build order`) | gapless numbered steps, fenced block |
| 6 | `Priority` (any `priority` line) | conflict rule, e.g. `spec > ortho > master > detail` |

Missing any of the six → validator FAIL.

A seventh, optional section: `Geometry` (`## Geometry`). See below.

## Field types

| Field | Type | Example |
|---|---|---|
| length | number + unit (`mm`/`m`) | `` ~`35×28×25 mm` `` |
| color | `#RGB` / `#RRGGBB` / `#RRGGBBAA` | `#7EA6FF` |
| tolerance | `±` number + unit | `±3 mm` |
| object name | `PREFIX_rest`, caps prefix | `CTX_Frontal` |
| camera | `` `CAM_Name` `` + lens/framing | `` `CAM_Master` — 3/4 overview, 16:9 `` |
| build step | `NN description` (`01`…`NN`, gapless from 1) | `04 cortical regions` |
| label | exact display text + subtitle | `Thalamus — Sensory relay…` |

## Required vs optional

- Required: units + axes, palette (≥1 hex), collections tree,
  ≥1 camera, gapless build order, priority rule, exact label strings.
- Optional: lighting, render settings, animation-readiness notes,
  acceptance checklist, reference-image set, geometry.
- Optional sections MUST NOT contradict required ones.

## Normative rules

1. MUST: every color is a well-formed hex (`#RGB`/`#RRGGBB`/`#RRGGBBAA`);
   build steps start at `01` with no gaps; ≥1 camera named `CAM_*`.
2. MUST: the priority rule names the spec file authoritative —
   `SCENE_SPEC.md` outranks renders and reference views on conflict.
3. SHOULD: dimensions carry explicit units; names carry their
   collection prefix; labels are quoted exactly as displayed.

## Geometry (optional, additive)

`## Geometry` gives any object real primitives instead of a proxy box. It is
JSON in a fence, not bullets, because a lathe profile or a jointed arm is
nested data and prose would be a worse contract than the thing it replaces:

```json
{
  "GLOW_Bulb": {
    "kind": "sphere",
    "radius": 0.03,
    "segments": 32,
    "rings": 16
  },
  "LAMP_LowerArm": {
    "kind": "arm",
    "joints": [[-0.012, 0, -0.13], [0.012, 0, 0.0], [-0.004, 0, 0.13]],
    "radius": 0.014,
    "joint_radius": 0.018,
    "caps": false,
    "segments": 20
  }
}
```

(lifted from `examples/desk-lamp/SCENE_SPEC.md`; `LAMP_Base` there also
shows the `group` composite: a turned cylinder plus a torus foot ring.)

The section is a fixpoint like every other: a spec with no `## Geometry`
parses and builds byte-identical to a spec written before this feature
existed — the `geometry` key is absent from the parsed dict, not an empty
object, and that absence is the regression test.

### Primitive vocabulary

Compiled by `spec/geometry.py`. Every block needs a `kind`; unknown kinds
fail closed (`GeometryError`).

| Kind | Fields | Notes |
|---|---|---|
| `box` | `size: [w, d, h]` | Defaults to a 50mm cube if omitted |
| `cylinder` | `radius` or `radius_bottom`/`radius_top`, `height`, `segments` | Equal top/bottom radius by default; a different `radius_top` gives a truncated cone |
| `cone` | `radius`, `radius_top` (default 0), `height`, `segments` | A cone is a cylinder with `radius_top: 0` |
| `sphere` | `radius`, `segments`, `rings` | UV sphere |
| `torus` | `radius`, `tube`, `segments`, `tube_segments` | Lies in the XY plane |
| `lathe` | `profile: [[radius, z], ...]` (≥2 points), `segments` | Revolves the profile around +Z |
| `extrude` | `outline: [[x, y], ...]` (≥3 points), `depth` | Sweeps a closed 2D outline along +Z |
| `group` | `pos`, `parts: [block, ...]` (non-empty) | Composite: translation only, compiles away into its children |
| `arm` | `joints: [[x, y, z], ...]` (≥2), `radius`, `joint_radius`, `segments`, `caps` | Composite: a jointed polyline becomes one aimed cylinder per segment plus one sphere per joint (or per interior joint only, if `caps: false`) |

Every leaf block may also carry `pos: [x, y, z]` and either `quat: [x, y, z, w]`
or `rot_deg: [rx, ry, rz]` (intrinsic X, then Y, then Z — converted to a
quaternion at compile time). `group` and `arm` are composites: they never
appear in a compiled `parts` list, only their leaf output does.

### Conventions (normative)

- **Z up, metres** — matches the Units section. Every axial primitive
  (cylinder, cone, lathe) runs along **+Z**; a torus lies in the **XY**
  plane; an extrusion sweeps along **+Z**.
- **Quaternions, never Euler angles**, leave the compiler: `[x, y, z, w]`.
  Author with `rot_deg` if degrees are easier; it's converted once, at parse
  time.
- **A `group` carries translation only.** A `rot_deg`/`quat` on a group is a
  `GeometryError`, not a silently dropped rotation — put the rotation on the
  leaf parts instead.
- **Nothing is rescaled to fit `size_mm`.** If the compiled parts' bounding
  box disagrees with the object's declared dimensions by more than 1mm
  (`FIT_TOLERANCE_M`), the compiler adds a warning to `build.json` and
  leaves the geometry exactly as authored. A mismatch is a bug in the spec
  or the geometry, never something to paper over by stretching the mesh.

### Blockout fallback

An object with no entry in the `## Geometry` map — or a spec with no
`## Geometry` section at all — gets one box sized to its declared envelope,
labelled `source: "blockout"` in `build.json`. An object that does have an
entry gets `source: "modelled"`. Once any object in a scene is modelled,
every object in that build carries a `source`, so nothing in `build.json`
leaves a reader guessing which boxes are real geometry and which are
proxies.

### The overlap gate reads this too

`qa/asserts.no_overlap` is implemented, not a stub: it takes the world AABB
of every compiled part (one box per arm link, not one loose box around the
whole arm) and fails a pair only if some part of one interpenetrates some
part of the other on all three axes by more than the tolerance. That
tolerance is not a constant in the checker — `qa/asserts.spec_tolerance_m`
reads it out of the spec's own Units prose (e.g. `Placement tolerance: major
forms ±5 mm`), taking the largest value stated. No tolerance line means
zero slack.

## How the parser reads it (`spec/scene_spec.py`)

The validator checks the six required sections. The parser reads more, and
these rules are normative — they decide what reaches both backends.

| What | Where it is read from |
|---|---|
| `title`, `scene` | first `# ` heading; `scene` is the slug with a trailing "Scene Spec" removed |
| `units` | the Units section's bullets, kept verbatim as `notes`; `X up` sets the axis, `metric` sets the system, `<Name> envelope: \`a × b × c m\`` fills `envelopes`, any bullet with `±` is a tolerance |
| `palette` | ANY section: a bullet of `Name \`#HEX\`` (optionally ` alpha 0.5 roughness 0.4`), or a `material: #HEX` line, which is named after its section. A section-level `alpha`/`roughness` line applies to that section's entries. Hex is matched longest-first, so `#E8EEF3` never truncates to `#E8E` |
| `collections` | the first fenced block in the Collections section; box-drawing characters stripped, `SCENE` dropped |
| `objects` | `PREFIX_Name` tokens (2+ capitals, then a suffix) in the Naming section, in order |
| collection per object | an explicit `PREFIX_ -> COLLECTION` line in Naming, else a synonym table (`CTX`→CORTEX, `SUB`→SUBCORTICAL, …), else the first collection whose name contains the prefix |
| `size_mm` | a dimensioned bullet anywhere, matched by object name then by suffix: `35 × 28 × 25 mm`, or a single `~40 mm` for all three axes. Undimensioned objects get a documented default, not a guess |
| `labels` | the Functional labels section: `Name — subtitle` |
| label per object | the longest label whose normalized text contains the object's suffix |
| `cameras` | every `CAM_*` in the Cameras section, in order, with the text after the em dash as `desc` |
| `build_order` | numbered lines in the Deterministic build order fenced block |
| `priority` | the text after `Conflict priority:`, or the next non-empty line |
| `render` | the Render section's `master`/`orthographic` resolutions and engine; background hex from Lighting |
| `geometry` | the `## Geometry` section's single fenced JSON object, name → block, verbatim; absent (not `{}`) when the section is absent — see "Geometry" above |

Nothing is invented. A colour with no name, a shape the spec never
dimensions, or an object no label matches stays unset and takes a
documented default.

## Derived build JSON (`to_build_json`)

Placement is computed, not authored: objects are packed into a grid, one
column per widest object, one row per deepest, gap scaled to the median
object. Cameras get positions from their names (`Left`/`Front`/`Top`/
`Detail`/`Exploded`/default 3-quarter) and the scene extent; `Orthographic`
in the name makes the camera orthographic. Views pair one PNG per camera at
the master or orthographic resolution.

If the scene has a `## Geometry` section, every object also gets a compiled
`geometry` entry (`spec/geometry.py`'s `compile_object_geometry`), keyed by
the object's own declared size in metres — including objects with no block
of their own, which get the labelled blockout box. A scene with no
`## Geometry` section produces objects with no `geometry` key at all.

`build_sha256` is sha256 over that JSON, sorted keys, tight separators. Same
spec bytes, same hash, any machine. `spec_sha256` pins the Markdown itself.

## Round trip

`emit_spec(parse_spec(text))` is a **fixpoint**, not a byte copy: the emitted
file passes the validator and parses back into the identical dict. Golden
files and the fixpoint check live in `tests/golden/` and `tests/test_all.py`.

## Minimal skeleton

```markdown
# <Scene> Scene Spec
## Units and coordinates
## Collections
## Cameras
palette: - <Name> `#RRGGBB`
## Deterministic build order
Conflict priority: `scene_spec.md > …`
```
