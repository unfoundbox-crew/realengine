# SCENE_SPEC.md — Schema (v0.1.0)

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
