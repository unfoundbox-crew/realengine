# code-to-3d — Agent Spec (v0.1.0 target)

> Read this before touching the tree. Normative unless marked `prose`.

## 1. What this is

Prompt → pinned spec → deterministic 3D on two backends, machine-checked QA,
two human gates. Category: code-to-3D the way HyperFrames did code-to-video.
License: Apache 2.0. Name: `intent3d` shortlist pending — tree stays
`code-to-3d` until the rename lands.

## 2. The split (load-bearing, do not redesign)

- Agents own determinism. Humans own taste.
- `SCENE_SPEC.md` is the only artifact both read.
- Human Gate 1: approve the spec. Human Gate 2: the eye.
- QA machines check (legible, match, no-overlap); taste is never automated.

## 3. Tree contract

```
spec/     SPEC-SCHEMA.md + validate.py + scene_spec.py (md<->json round trip)
          + llm.py (the one model call) + compile_brief.py (prompt->spec)
blender/  ctd_blender lib (collections, materials, blockout, lighting,
          cameras, qa) + build.py + run_headless.py
web/      template_scene.html (generic) + template.html + presets/*.json
          + build_web.py (slots) + build_scene.py (spec->scene) + render_views.py
qa/       asserts.py + run_qa.py (zero-vision subprocess, --json receipts)
tools/    export_scene.py (deterministic zip of a built scene)
skill/    code-to-3d/SKILL.md + scripts/ + references/
mcp/      code-to-3d-mcp (6 tools, each running the step that owns the job)
examples/ one dir per scene: SCENE_SPEC.md + refs + final/
tests/    test_all.py + golden/ (pinned scene json, emitted md, hashes)
docs/     ARCHITECTURE.md, ROADMAP.md, TECH-DESIGN.md, AUDIENCE.md,
          BACKENDS.md, BUILD-PLAN.md, charts/
```

## 4. Interfaces (stable)

- Spec schema: `spec/SPEC-SCHEMA.md`. Validator MUST pass on every spec.
  Palette lives in `## Palette`. Cameras ≥1. Build steps gapless.
- Blender lib: no `bpy` import at module top (import-safe without Blender);
  all paths/params are arguments (grep `/Users/` MUST be empty).
- Web: every scene string is a `{{slot}}`; `build_web.py` fails loud on
  unbound slots or surviving `{{...}}`; geometry stays code, copy stays slots.
- QA: `run_qa.py --renders DIR --labels CSV`, exit 0 iff all pass. Run on
  full-res masters only (small-preview OCR garble is a known trap).
- MCP tools (exact 6): `brief, spec_compile, build, views, qa_assert,
  export_scene`. Each runs a Python step and returns its JSON receipt; a
  step whose dependency is missing returns `ok:false` naming it. No silent
  fallback, ever.
- Spec round trip: `SCENE_SPEC.md` -> build JSON is code (`spec/scene_spec.py`),
  pinned by `build_sha256`. Emitting a spec back out MUST be a fixpoint.
- Model use: exactly one step (`brief`) may call a model, through an
  OpenAI-compatible base URL taken from the environment. Everything after
  the spec exists MUST run offline.
- Skills: frontmatter triggers, body <100 lines, references on demand.

## 5. Conventions (CI-enforced where possible)

- Seeded determinism everywhere randomness appears.
- No silent cloud fallback, ever. Engines fail closed with install hints.
- Every lane delivers a receipt: test output, bytes, counts.
- Subagents report to coordinator in ONE final message; never spawn, never
  message sideways. Briefs carry FINAL MESSAGE FORMAT.
- Heavy compute leaves the MacBook (lenovo / self-hosted CI).

## 6. Backends

RIDE: Blender (MCP + headless bpy, free), Three.js (agents dream in HTML).
WATCH: Babylon.js. INTEGRATE at FBX/glTF/USD: Unity, Unreal, Houdini.
SKIP: PlayCanvas, Godot. ROUTE AROUND: seat-licensed API-less DCC.
Never fight an engine; meet giants at file formats.

## 7. Money (recorded, not built at 0.1.0)

Core free forever (spec, builders, QA, skill, validator, formats). Paid =
metered metal and servers only (burst previews, gallery, teams). BYOK
inference on their keys. Burst ladder: own fleet (GPUStack) → SkyPilot
router → Render Network / Vast spot → Beam/Modal DX premium last.

## 8. Done gates (0.1.0 ships iff ALL hold)

1. Prompt + refs → spec → `.blend` AND `.html`, zero hand edits.
2. QA catches an injected label overlap unaided.
3. Third-party agent installs skill + MCP, builds a novel scene solo.
4. One-command install; README design/table pattern; OIDC release flow.
