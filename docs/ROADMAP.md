---
title: RealEngine Roadmap
product: realengine
version: 3.0.0
status: living
updated: 2026-09-12
horizon: 2026-Q4
---

## Now (this week)

- [ ] Pass `--build` through the MCP `qa_assert` tool — why it matters: `no_overlap` is real and `qa/run_qa.py --build build.json` already folds an overlap verdict into its receipt, but the MCP tool does not forward the argument, so an agent calling `qa_assert` still gets only the label verdict and SPEC.md done-gate #2 ("QA catches an injected overlap unaided") is not reachable through the tools an agent actually calls — done when: `qa_assert` accepts a build path, returns the overlap verdict alongside the label verdict, and a test injects an overlapping pair through that tool and gets a failure naming both objects.
- [ ] Prove `brief` against the live proxy — why it matters: only the stubbed and fail-closed paths have run; `LITELLM_BASE_URL` is not in the Doppler config, so nobody has seen a real draft — done when: one `brief` call with the proxy configured produces a spec that passes `check_spec` first try, and the model id used is recorded here.
- [ ] Re-render the Blender backend now that it has lights and modelled geometry — why it matters: the one proven headless frame came out black (no lights) and predates the geometry compiler entirely — done when: a `.blend` + a non-black PNG of the desk-lamp (turned base, jointed arms, lathed shade) come out of `blender/run_headless.py` and the receipt is pasted into this file.

## Next (this month)

- [ ] Make `no_overlap` tighter than axis-aligned boxes for the diagonal case — why it matters: the AABB method the compiler ships is exact for spheres and bodies of revolution but a true hull test for two slim diagonal bodies can still false-positive, which the docstring already admits — done when: a test with two diagonally-crossing arm links either passes correctly or the trade-off is written down as accepted, not just discovered.
- [ ] Label placement that survives dense views — why it matters: `CAM_FrontOrthographic` and `CAM_Detail` fail the OCR gate on both examples because labels stack or fall outside the crop, and that is the pipeline's own output failing its own gate — done when: every view of both examples passes `qa_assert` with the default engine.
- [ ] Make the OCR engine choice honest across platforms — why it matters: measured on these renders, the portable default (tesseract) misses labels `apple-vision` reads cleanly, which is why CI's OCR step is still `continue-on-error` rather than a hard gate — done when: the default is documented per platform in README and `qa/asserts.py`, or the frames are rendered legibly enough for tesseract and the CI step becomes a hard gate.
- [ ] Vendor or inline three.js — why it matters: the "standalone" page needs network on first open, so a headless render on an offline box fails — done when: a built page renders with the network off, or the docs stop calling it self-contained.
- [ ] Extend the primitive vocabulary or explicitly cap it — why it matters: `spec/geometry.py` covers box/cylinder/cone/sphere/torus/lathe/extrude plus `group`/`arm`, which handled the desk-lamp; a subject needing a shape outside that set still falls back to a blockout box with no way to say why — done when: either a new primitive lands with the same test rigor (compiler + tessellation + template mapping), or `SPEC-SCHEMA.md` states the vocabulary is closed for now and why.

## Later (this quarter)

- [ ] Generalize `examples/brain/`'s ad hoc numbered scripts (`01_rebuild.py`…`11_final_adjustments.py`) into the `ctd_blender` pipeline, or archive them clearly as legacy seed material — why it matters: right now the one finished, real scene isn't proof the generalized backend works end to end — done when: a second example scene builds through `build.py`/`ctd_blender` alone, no numbered one-off scripts.
- [ ] Third-party agent install test (SPEC.md done-gate #3) — why it matters: nobody outside this repo's own sessions has installed the skill + MCP and built a novel scene — done when: a different agent/session, with no prior context, builds a novel (non-brain) scene solo from the published skill.
- [ ] Add the `/Users/` path grep SPEC.md section 4 requires ("grep `/Users/` MUST be empty") as an actual CI check — why it matters: it's written as a MUST but nothing enforces it today — done when: a CI step runs that grep and fails the build on a hit.

## Not doing (and why)

- Hosted rendering / burst compute (GPUStack, SkyPilot, Render Network, Beam/Modal) — TECH-DESIGN.md section 5 and SPEC.md section 7 both mark this "recorded, not built at 0.1.0"; self-hosted lenovo covers CI needs for now.
- Mesh-gen training, a visual editor, a React wrapper, a DocIR-3D bridge — explicit non-goals, TECH-DESIGN.md section 5.
- Babylon.js, PlayCanvas, Godot, Unity/Unreal/Houdini as first-class backends — BACKENDS.md verdicts: WATCH / SKIP / INTEGRATE-at-file-border only; Three.js and Blender are the only RIDE backends.

## Shipped

| Date | Item | Commit/PR |
|---|---|---|
| 2026-09-12 | `SCENE_SPEC.md` ⇄ build JSON round trip, pinned by sha256, with golden and fixpoint tests | 7e2090d |
| 2026-09-12 | Real Three.js backend (`web/build_scene.py` + generic template), headless view renderer, QA `--json` receipts, deterministic scene zip | 75542df |
| 2026-09-12 | Prompt→spec compiler (`spec/compile_brief.py`, `spec/llm.py`) and a Blender backend that builds blockout + lights, plus the headless argv convention | 29e6b62 |
| 2026-09-12 | All six MCP tools doing real work, schemas matching handlers, hermetic transport test | 90d56ef |
| 2026-09-12 | Compiler and web-backend tests; CI round-trip and deterministic-scene-build steps | d319240 |
| 2026-09-12 | Packed blockout layout and `examples/desk-lamp`, a second non-brain example | 7321fc3 |
| 2026-09-11 (unverified date, from `git log`) | Audit fixes, unified `tests/test_all.py`, GitHub Pages portal (`index.html`, `tracker.html`) | a96785c |
| 2026-09-12 | Blockout-vs-stage question answered: an optional `## Geometry` section + `spec/geometry.py` compiler (box/cylinder/cone/sphere/torus/lathe/extrude, `group`/`arm` composites), `blender/ctd_blender/primitives.py` tessellation with no `bpy`, and `examples/desk-lamp` remodelled with real primitives | 7baa200 |
| 2026-09-12 | `qa/asserts.no_overlap` implemented (was `NotImplementedError`): part-wise AABB intersection, tolerance read from the spec's own placement-tolerance prose | 7baa200 |
| 2026-09-12 | CI `views` job: headless Chromium renders the desk-lamp's four camera views, `qa/png_stats.py` asserts they aren't black, tesseract OCR gate runs best-effort, PNGs uploaded as artifacts | 7baa200 |

## Decision log

| Date | Decision | Alternatives rejected | Link |
|---|---|---|---|
| 2026-09 (TECH-DESIGN.md, undated within doc) | Ride Blender + Three.js only; integrate Unity/Unreal/Houdini at file-format border (FBX/glTF/USD); route around seat-licensed API-less DCCs | Building/competing head-on with heavyweight DCC editors | `docs/BACKENDS.md`, `TECH-DESIGN.md` section 5c |
| 2026-09 (TECH-DESIGN.md 5b) | Sell outcomes (spec in, verified scene out) via a tiny ~6-verb MCP surface, not a large tool zoo like other Blender MCP servers | Exposing raw bpy/GL verbs (the "86 tools" pattern named in 5b) | `TECH-DESIGN.md` section 5b |
| 2026-09-12 | One model call only, at `brief`; everything after the spec is code, offline, and hash-pinned | A model in the build loop; per-backend prompting | `spec/llm.py`, `spec/compile_brief.py` |
| 2026-09-12 | Backends render a blockout from what the spec states, and invent nothing about the subject | Filling gaps with plausible geometry | `docs/ARCHITECTURE.md` Purpose |
| 2026-09-12 | The blockout is a stage, not the product: an object gets modelled primitives if the spec's `## Geometry` section describes it, a labelled proxy box otherwise; nothing is ever rescaled to fit the declared size | Inventing geometry the spec doesn't state; silently rescaling a mismatch | `spec/geometry.py` module docstring |
| 2026-09-12 | Optional dependencies (Blender, headless browser, model endpoint) fail closed by name and are never simulated | A "demo mode" that fakes renders | `mcp/src/handlers.ts` |
| 2026-09 (SPEC.md section 1) | Tree stays named `code-to-3d` until a rename to `intent3d` (shortlisted, not decided) lands | Renaming immediately | `SPEC.md` section 1 |
