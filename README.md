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
3. **Machine QA Loop**: Zero-Vision reads render pixels as text (checking label legibility, camera envelopes, and overlap) *before* asking the human eye to judge taste.

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

## Packages

| Dir | Package | In | Out |
|---|---|---|---|
| `spec/` | Spec schema + validator (`validate.py`) | markdown / words | `SCENE_SPEC.md` (valid) |
| `blender/` | `ctd_blender` bpy library + `build.py` | spec | `.blend` + QA PNGs |
| `web/` | Three.js template + preset JSON + `build_web.py` | spec preset | self-contained HTML + snapshot |
| `qa/` | `asserts.py` + `run_qa.py` (zero-vision OCR) | renders dir | pass / fail + missing labels |
| `mcp/` | Model Context Protocol TypeScript server (6 tools) | MCP call | structured result |
| `tests/` | Unified test suite (`test_all.py`) | — | test receipts |

---

## Quickstart

### 1. Validate a Scene Spec
```bash
python3 spec/validate.py examples/brain/SCENE_SPEC.md
```

### 2. Build Web 3D Scene (Deterministic)
```bash
python3 web/build_web.py web/presets/brain.json web/template.html web/build/brain.html
open web/build/brain.html
```

### 3. Run the Machine QA Gate
```bash
python3 qa/run_qa.py --renders examples/brain --labels "Thalamus,Hippocampus,Amygdala"
```

### 4. Run the Full Test Suite
```bash
python3 -m unittest discover -s tests -p 'test_*.py'
cd mcp && npm test
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
