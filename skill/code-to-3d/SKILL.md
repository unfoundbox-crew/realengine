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
5. **Write spec** — emit `SCENE_SPEC.md` per `spec/SPEC-SCHEMA.md`;
   run `python3 spec/validate.py` until PASS.
6. **Human Gate 1** — spec approval. Last readable checkpoint. No
   build without it.
7. **Build** — `build.py` (Blender: `.blend` + QA PNGs) and web
   template (Three.js HTML + snapshot PNG). Seeded, deterministic.
8. **QA** — machine checks only: `qa/` asserts (legible, match,
   no-overlap) read renders as text via zero-vision. Fix, rebuild.
9. **Human Gate 2 (eye)** — show master render; approve or one-line
   correction, then rebuild. The only un-automatable step.

## Rules

- `SCENE_SPEC.md` outranks all renders on conflict.
- Fail-closed engines: local first, never silent cloud (see
  `references/RANK.md`).
- No random placement; no invented labels, regions, or claims.
- Small files only — every line earns context-window rent.

## Consumes

| Input | Output |
|---|---|
| words + refs | valid `SCENE_SPEC.md` → `.blend` + `.html` + QA PNGs |
