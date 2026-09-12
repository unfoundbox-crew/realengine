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
  acceptance checklist, reference-image set.
- Optional sections MUST NOT contradict required ones.

## Normative rules

1. MUST: every color is a well-formed hex (`#RGB`/`#RRGGBB`/`#RRGGBBAA`);
   build steps start at `01` with no gaps; ≥1 camera named `CAM_*`.
2. MUST: the priority rule names the spec file authoritative —
   `SCENE_SPEC.md` outranks renders and reference views on conflict.
3. SHOULD: dimensions carry explicit units; names carry their
   collection prefix; labels are quoted exactly as displayed.

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
