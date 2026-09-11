# code-to-3d

prompt → pinned spec → deterministic 3D on two backends, with a machine-checked QA loop and exactly two human gates.

## Architecture

```
HUMAN (intent · taste · go)
  │  words in
  ▼
SKILL code-to-3d — any agent, ~100 tokens idle
  brief → research → refs → questions → options → SPEC
  ▼
SPEC (SCENE_SPEC.md — the contract)
  ▼  HUMAN GATE 1
MCP tiny surface (~6 verbs: brief · spec · build · views · qa · export)
  ├──► BLENDER backend (spec → bpy lib → .blend + QA PNGs)
  └──► WEB backend (spec → Three.js template → HTML + snapshot PNG)
  ▼ renders
QA LOOP — machine-checkable only (zero-vision reads pixels as text)
  ▼
HUMAN GATE 2 (the eye — the only un-automatable step)
  ▼
SHIP — tag → build → test → publish (CI, OIDC, provenance)
```

Cross-cutting: progressive disclosure · fail-closed engines (never silent
cloud) · seeded determinism · skills + llms.txt versioned with the code.

## Packages

| Dir | Package | In | Out |
|---|---|---|---|
| `spec/` | Spec schema + validator + prompt→spec compiler | words + refs | `SCENE_SPEC.md` (valid) |
| `blender/` | bpy library (collections, materials, cameras, labels, QA) + `build.py` | spec | `.blend` + QA PNGs |
| `web/` | Three.js template + preset JSON | spec | self-contained HTML + snapshot PNG |
| `qa/` | zero-vision asserts (legible, match, no-overlap) | renders | pass/fail + diff |
| `skill/` | `code-to-3d/SKILL.md` + scripts + references | — | installable skill |

Seed material: `examples/brain/` (brain session: 11 builder scripts + spec +
references), `web/examples/brain-v2.html` (web template reference).

## Quickstart (stub — workstreams B–E fill this in)

```bash
# 1. Write a brief, compile it to a pinned spec (workstream B)
./spec/compile --brief brief.md --out SCENE_SPEC.md
# 2. Human Gate 1: approve SCENE_SPEC.md
# 3. Build both backends (workstreams C, D)
./blender/build.py --spec SCENE_SPEC.md --out out.blend
open web/examples/brain-v2.html
# 4. Machine QA loop (workstream E), then Human Gate 2 (the eye)
./qa/check --renders out/
```

## License

Apache 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
