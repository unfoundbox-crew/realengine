# RealEngine

> *Why build Unreal when you can declare what's Real?*

Prompt → pinned spec → deterministic 3D on two backends (Blender & Three.js), with a machine-checked QA loop and exactly two human gates.

[![ci](https://github.com/unfoundbox-crew/realengine/actions/workflows/ci.yml/badge.svg)](https://github.com/unfoundbox-crew/realengine/actions/workflows/ci.yml)
[![Pages](https://github.com/unfoundbox-crew/realengine/actions/workflows/pages.yml/badge.svg)](https://unfoundbox-crew.github.io/realengine/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

---

## The Core Inversion

3D generation is broken because diffusion models spit out uneditable, non-deterministic polygon soup. You can't rig it, you can't diff it in git, and you can't animate it without messy retopology.

**RealEngine inverts this:**
1. **Spec is King**: Human intent compiles into a human-readable, machine-checked contract (`SCENE_SPEC.md`).
2. **Deterministic Backends**: The same spec compiles to native Blender `.blend` files (procedural materials, modifier stacks, aimed cameras) and self-contained Three.js WebGL scenes.
3. **Machine QA Loop**: Zero-Vision reads render pixels as text (label legibility) *before* asking the human eye to judge taste. Overlap detection is still a stub — see [what works](#what-works-today).

---

## Architecture

```
HUMAN (intent · taste · go)
  │  words in
  ▼
SKILL realengine — any agent, ~100 tokens idle
  brief → research → refs → questions → options → SPEC
  ▼
SPEC (SCENE_SPEC.md — the authoritative contract)
  ▼  [HUMAN GATE 1: approve spec]
MCP tiny surface (~6 verbs: brief · spec_compile · build · views · qa_assert · export_scene)
  ├──► BLENDER backend (spec → bpy lib → .blend + QA PNGs)
  └──► WEB backend     (spec → Three.js template → standalone HTML + snapshot PNG)
  ▼ renders
QA LOOP — machine-checkable only (zero-vision OCR reads pixels as text)
  ▼
HUMAN GATE 2 (the eye — the only un-automatable step)
  ▼
SHIP — tag → build → test → publish (CI, GitHub Pages, OIDC)
```

Cross-cutting principles:
- **Progressive disclosure**: 100-token idle footprint, expands on demand.
- **Fail-closed engines**: Zero silent cloud fallbacks, deterministic local execution.
- **Seeded determinism**: Same spec + seed = byte-identical web output.
- **Audience & Spec parity**: Code, tests, and `SPEC-SCHEMA.md` versioned together.

---

## What works today

Honest status, verified on this commit. "Blockout" means one named proxy
volume per named object in the spec, at its stated size, in its palette
colour, labelled, under the spec's own cameras — the builder renders what
the spec says and invents nothing.

| MCP tool | State | Needs |
|---|---|---|
| `brief` | Real. Drafts a `SCENE_SPEC.md`, rejects it unless the validator passes and it parses complete, retries once with the failures fed back | An OpenAI-compatible base URL + key in the environment; fails closed by name without them |
| `spec_compile` | Real. Spec → pinned build JSON + both hashes | Nothing. Offline, deterministic |
| `build` (`web`) | Real. Standalone Three.js page + `build.json` + `views.json` | Nothing to build. The page pulls three.js from a CDN on first open |
| `build` (`blender`) | Real. `.blend` + PNGs via headless Blender | A Blender binary (`REALENGINE_BLENDER`, PATH, or the macOS bundle) |
| `views` | Real. PNGs of every named camera | Headless Chromium via Playwright. Without it: no PNGs, exit 3, and the `?view=` URLs any browser can drive |
| `qa_assert` | Real. OCR label gate (+ optional `views_match`) | Rendered PNGs and zero-vision. `no_overlap` is still a stub |
| `export_scene` | Real. Deterministic zip with a sha256 manifest, or one html/png | Nothing |

Known gaps, stated plainly: `qa/asserts.no_overlap` raises
`NotImplementedError`; the Blender backend builds a blockout, not modelled
geometry; CI runs neither the browser nor the OCR gate (no browser and no
zero-vision in that image), so both are local steps.

## Packages

| Dir | Package | In | Out |
|---|---|---|---|
| `spec/` | Schema + `validate.py` + `scene_spec.py` (md ⇄ JSON) + `compile_brief.py` (prompt → spec) + `llm.py` | words or `SCENE_SPEC.md` | valid spec, build JSON, `build_sha256` |
| `blender/` | `ctd_blender` bpy library + `build.py` + `run_headless.py` | build JSON | `.blend` + QA PNGs |
| `web/` | `build_scene.py` + `template_scene.html` + `render_views.py` (plus the legacy slot builder `build_web.py`) | spec or build JSON | standalone HTML + `views.json` + PNGs |
| `qa/` | `asserts.py` + `run_qa.py` (zero-vision OCR, `--json` receipts) | renders dir | pass / fail + missing labels |
| `tools/` | `export_scene.py` | scene dir | deterministic zip + sha256 manifest |
| `mcp/` | Model Context Protocol TypeScript server (6 tools) | MCP call | the step's JSON receipt |
| `tests/` | `test_all.py` + `golden/` (pinned JSON, emitted md, hashes) | — | test receipts |

---

## Quickstart

### 1. Words → spec (the only step that calls a model)
```bash
# base URL and key come from the environment; nothing is hardcoded
doppler run --project unfoundbox --config dev_personal -- \
  python3 spec/compile_brief.py brief --prompt "a jointed desk lamp on a workbench"
```
Needs `REALENGINE_LLM_BASE_URL` (or `LITELLM_BASE_URL`) and
`REALENGINE_LLM_API_KEY` (or `LITELLM_MASTER_KEY`); model defaults to
`claude-sonnet-4-6` (verified live on the proxy 2026-09-12; `claude-sonnet-5`
and `claude-fable-5` 500 there today, Bedrock models not enabled),
`REALENGINE_LLM_MODEL=gemini-3.7-flash` for a cheap draft when it's not out
of quota. Missing either → a named error, no fallback. **Human Gate 1: read
the spec.** Everything below is offline.

### 2. Spec → pinned build JSON
```bash
python3 spec/scene_spec.py hash examples/desk-lamp/SCENE_SPEC.md
python3 spec/compile_brief.py compile --spec examples/desk-lamp/SCENE_SPEC.md --out-dir out/lamp
```

### 3. Build a scene
```bash
# web: a standalone page + build.json + views.json
python3 web/build_scene.py examples/desk-lamp/SCENE_SPEC.md --out-dir out/lamp
open out/lamp/scene.html

# blender: .blend + PNGs, needs Blender installed
python3 blender/run_headless.py --spec out/lamp/build.json --out-dir out/lamp/blender
```

### 4. Render QA views, then gate them
```bash
python3 web/render_views.py --scene-dir out/lamp          # needs headless Chromium
python3 qa/run_qa.py --renders out/lamp/renders \
  --labels "Base,LowerArm,UpperArm,Shade,Bulb" --engine apple-vision
```
No browser? `views.json` carries a `?view=CAM_Name&hud=0` URL and a target
resolution per camera, and the page sets `window.REALENGINE_READY` when the
frame is settled — drive it with any browser you like.

### 5. Ship it
```bash
python3 tools/export_scene.py --scene-dir out/lamp
```

### 6. Run the full test suite
```bash
python3 -m unittest discover -s tests -p 'test_*.py'
cd mcp && npm ci && npm run build && npm test
```

### Using it as an MCP server
```jsonc
{ "command": "node", "args": ["mcp/dist/index.js"],
  "env": { "REALENGINE_ROOT": "/path/to/realengine",
           "REALENGINE_PYTHON": "python3" } }
```

---

## Live Demo & Build Tracker

- **Interactive 3D WebGL Viewer**: [https://unfoundbox-crew.github.io/realengine/](https://unfoundbox-crew.github.io/realengine/)
- **Live Build Tracker**: [https://unfoundbox-crew.github.io/realengine/tracker.html](https://unfoundbox-crew.github.io/realengine/tracker.html)

---

## License

Apache 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).

## Living docs

Architecture and roadmap: `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`. Rendered page: https://claude.ai/code/artifact/74ed6218-f9fc-4921-97aa-9484c359d69c
Rebuild: `python3 docs/site/build.py --arch docs/ARCHITECTURE.md --roadmap docs/ROADMAP.md --out docs/site/index.html --product-name RealEngine --repo-url https://github.com/unfoundbox-crew/realengine`
