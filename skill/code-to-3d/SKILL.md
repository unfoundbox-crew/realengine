---
name: code-to-3d
description: >-
  Build a deterministic 3D scene from words. Use when the job is a 3d scene,
  blender model, three.js page, render of an object or diagram in 3D, or
  "turn this idea into 3D". Writes SCENE_SPEC.md, builds Blender + web
  backends, runs machine QA, then asks the human eye. Never silent cloud.
---

# code-to-3d

Prompt → pinned spec → deterministic 3D on two backends. Agents own
determinism; humans own taste. The spec is the only artifact both read.

## Workflow

1. **Research web** — look up the subject (anatomy, proportions,
   reference images). Save URLs into the spec's refs.
2. **Ask refs** — request images, dimensions, palette from the human.
3. **Clarifying questions** — one round, plain options, then proceed.
4. **Present options** — 2–3 directions (scope/fidelity/style) with
   token cost each. Human picks one.
5. **Write spec** — MCP `brief` drafts `SCENE_SPEC.md` and checks it,
   or write it by hand per `spec/SPEC-SCHEMA.md`. Either way
   `python3 spec/validate.py` must PASS. This is the last step that
   touches a model.
6. **Human Gate 1** — spec approval. Last readable checkpoint. No
   build without it.
7. **Compile** — MCP `spec_compile` (or
   `python3 spec/compile_brief.py compile --spec …`) pins the spec to
   `build.json` + `build_sha256`. Offline from here on.
8. **Build** — MCP `build` with backend `web` (standalone Three.js page
   + `views.json`) and/or `blender` (`.blend` + PNGs, needs Blender).
   Same build JSON, both backends.
9. **Views** — MCP `views` renders each named camera. No headless
   browser? `views.json` gives a `?view=…&hud=0` URL and a resolution
   per camera; capture once `window.REALENGINE_READY` is true.
10. **QA** — MCP `qa_assert`: OCR label gate over the renders dir
    (`no_overlap` is still a stub — overlap is eye-only). Fix, rebuild.
11. **Human Gate 2 (eye)** — show the master render; approve or take a
    one-line correction, then rebuild. The only un-automatable step.
12. **Ship** — MCP `export_scene` (zip: page + JSON + spec + manifest
    + renders, with sha256s).

## Rules

- `SCENE_SPEC.md` outranks all renders on conflict.
- Fail-closed engines: local first, never silent cloud (see
  `references/RANK.md`).
- No random placement; no invented labels, regions, or claims.
- Small files only — every line earns context-window rent.
- A tool that returns `ok:false` with a `requirement` is telling you a
  dependency is missing (Blender, headless Chromium, a model endpoint).
  Report it; never work around it with a fake result.
- The backends draw a blockout: one named volume per named object, at
  the spec's dimensions. They do not model shapes the spec doesn't state.

## Consumes

| Input | Output |
|---|---|
| words + refs | valid `SCENE_SPEC.md` → `build.json` (hash-pinned) → `.html` + `.blend` + QA PNGs → `scene.zip` |
