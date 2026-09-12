# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project
targets SemVer once it ships v0.1.0 (see `SPEC.md`); `spec/scene_spec.py` is
independently versioned at 0.2.0, `spec/geometry.py` at 0.1.0.

## [Unreleased] — 2026-09-12

### Added

- `## Geometry` section in `SCENE_SPEC.md`: an optional, additive fenced-JSON
  block mapping object name to a geometry block. A spec with no section
  builds byte-identical to before (pinned by the brain example's build hash).
- `spec/geometry.py`: a pure, stdlib-only compiler from a geometry block to a
  flat list of primitive parts (`box`, `cylinder`, `cone`, `sphere`, `torus`,
  `lathe`, `extrude`), plus two composites that compile away (`group`,
  `arm`). Z up, metres, axial primitives along +Z, torus in the XY plane,
  extrusion swept along +Z. Rotation leaves the module as a quaternion
  `[x, y, z, w]`; a block may be authored with `rot_deg` and it's converted.
  A group carries translation only — rotating a group is a `GeometryError`,
  not a silent drop. Nothing is ever rescaled to fit the spec's declared
  size; a mismatch over 1&nbsp;mm (`FIT_TOLERANCE_M`) becomes a warning on
  the build, never a silent resize.
- Blockout fallback, always labelled: an object with no geometry block gets
  a box the size of its declared envelope, `source: "blockout"` in
  `build.json`. Once any object in a scene is modelled, every object in that
  scene carries a `source`, so a reader of `build.json` never has to guess
  which boxes are real geometry and which are proxies.
- `blender/ctd_blender/primitives.py`: tessellates the same compiled parts to
  `(verts, faces)` in pure Python, no `bpy`, so the primitive vocabulary is
  testable on a machine with no Blender installed.
- `web/template_scene.html`'s `partGeometry()`: maps one compiled part to one
  Three.js `*Geometry` (`BoxGeometry`, `SphereGeometry`, `TorusGeometry`,
  `CylinderGeometry` for both cylinder and cone, `LatheGeometry`,
  `ExtrudeGeometry`).
- `qa/asserts.no_overlap`: real, part-wise axis-aligned bounding-box
  intersection between named objects (one box per part, not one loose box
  per object — a jointed arm no longer collides with thin air). Tolerance is
  read from the spec's own placement-tolerance prose
  (`qa/asserts.spec_tolerance_m`), the largest stated value wins, and it
  never raises on a legitimate empty result. Also accepts flat 2D pixel
  boxes for the label-overlap case.
- `qa/png_stats.py`: mean-RGB check that a rendered PNG isn't a black frame
  (bit depth 8, colour types 0/2/4/6; stdlib zlib only).
- `examples/desk-lamp/SCENE_SPEC.md` gained a `## Geometry` section: a turned
  base, two jointed arms, a lathed shade, and a spherical bulb — the bench
  top stays a blockout box on purpose.
- CI: a `views` job (`.github/workflows/ci.yml`) on `ubuntu-latest` that
  installs Playwright Chromium, renders the desk-lamp's four camera views,
  asserts the PNGs aren't black via `qa/png_stats.py`, runs the OCR label
  gate with `tesseract` (best-effort, `continue-on-error`), and uploads the
  PNGs as build artifacts.
- Tests: `TestGeometryCompiler`, `TestGeometryInTheSpec`, `TestNoOverlap`,
  `TestPrimitiveTessellation` in `tests/test_all.py`, plus
  `tests/golden/desk-lamp.build.json` and `desk-lamp.hashes.json`.

### Changed

- `spec/scene_spec.py`: `to_build_json` now attaches a compiled `geometry`
  entry to every object once any object in the scene declares one; parsing
  and emitting the `## Geometry` section is a fixpoint like every other
  section.
- `blender/ctd_blender/blockout.py`: builds one Blender mesh object per
  compiled part (parented under an empty named after the object) when
  `geometry.source == "modelled"`, instead of always scaling a unit cube.
