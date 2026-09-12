---
title: RealEngine Roadmap
product: realengine
version: 1.0.0
status: living
updated: 2026-09-12
horizon: 2026-Q4
---

## Now (this week)

- [ ] Wire the MCP `build` and `views` tools to `blender/build.py` and `web/build_web.py` — why it matters: every doc (README, SPEC.md, TECH-DESIGN.md, index.html) presents the MCP server as the primary agent surface, but all 6 tools currently fail closed — done when: `build` with `backend: "web"` produces a real `.html` file and returns its path, not an error.
- [ ] Wire `qa_assert` to `qa/run_qa.py` — why it matters: it's the only tool that closes the "machine checks before the human eye" loop the whole pitch rests on — done when: calling `qa_assert` with a renders dir and label list returns real pass/fail, not a stub error.
- [ ] Add a CI step that runs `qa/run_qa.py` against a fixture render (or explicitly document why it can't) — why it matters: the QA loop is currently untested by CI; a regression there would ship silently — done when: `gh run list` shows a green CI run that includes an OCR/QA step, or `docs/ARCHITECTURE.md`'s known-gaps entry is updated to explain the blocker.

## Next (this month)

- [ ] Build the prompt→spec compiler named in SPEC.md's tree contract (`spec/` — currently only `validate.py` + `SPEC-SCHEMA.md` exist) — why it matters: BUILD-PLAN.md calls Phase B "load-bearing — everything composes if it's right," and half of B (the compiler) doesn't exist — done when: a `spec_compile` MCP call or CLI script turns a recorded brief into a `SCENE_SPEC.md` that passes `validate.py`.
- [ ] Decide and implement how `SCENE_SPEC.md` (Markdown) becomes the JSON that `build.py`/`build_web.py` actually consume — why it matters: today the schema calls `SCENE_SPEC.md` "the only artifact both read," but no code reads it into a build — done when: one command turns a validated `SCENE_SPEC.md` into the JSON preset/spec both builders accept, with a round-trip test in `tests/test_all.py`.
- [ ] Implement `qa/asserts.no_overlap` (currently `NotImplementedError`, with the algorithm already sketched in its docstring) — why it matters: SPEC.md's done-gate #2 requires the QA loop to "catch an injected label overlap unaided," and it can't yet — done when: a test injects an overlapping label pair and `no_overlap` fails it without human review.
- [ ] Document (or build) the headless-Blender invocation for `build.py` — why it matters: no wrapper script or CI step runs it; nobody outside this session's author has proven it actually renders — done when: a `blender --background --python ...` command is in the repo (README quickstart or a script) and produces a `.blend` + PNGs from `examples/brain`.

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
| 2026-09-11 (unverified date, from `git log`) | Audit fixes, unified `tests/test_all.py`, GitHub Pages portal (`index.html`, `tracker.html`) | a96785c |

## Decision log

| Date | Decision | Alternatives rejected | Link |
|---|---|---|---|
| 2026-09 (TECH-DESIGN.md, undated within doc) | Ride Blender + Three.js only; integrate Unity/Unreal/Houdini at file-format border (FBX/glTF/USD); route around seat-licensed API-less DCCs | Building/competing head-on with heavyweight DCC editors | `docs/BACKENDS.md`, `TECH-DESIGN.md` section 5c |
| 2026-09 (TECH-DESIGN.md 5b) | Sell outcomes (spec in, verified scene out) via a tiny ~6-verb MCP surface, not a large tool zoo like other Blender MCP servers | Exposing raw bpy/GL verbs (the "86 tools" pattern named in 5b) | `TECH-DESIGN.md` section 5b |
| 2026-09 (SPEC.md section 1) | Tree stays named `code-to-3d` until a rename to `intent3d` (shortlisted, not decided) lands | Renaming immediately | `SPEC.md` section 1 |
