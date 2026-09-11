# code-to-3d — Technical Design Spec (v0.1.0)

## 1. Thesis

HyperFrames proved the playbook for code-to-video: plain files agents already
write, seekable/deterministic output, skills, non-interactive CLI, Apache 2.0.
Nothing owns that slot for 3D. Mesh APIs stop at blobs, MCP servers stop at
execution, video frameworks stop at pixels.

code-to-3d = prompt → pinned spec → deterministic 3D on two backends, with a
machine-checked QA loop and exactly two human gates.

## 2. The split (load-bearing)

Agents own determinism. Humans own taste. The spec is the only artifact both
read. QA splits exactly at the taste line: machines check, the eye judges.

- Human Gate 1: approve `SCENE_SPEC.md` (last human-readable checkpoint).
- Human Gate 2: the eye — approve or one-line correction, rebuild.

## 3. Architecture

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

## 4. Packages (this repo)

| Dir | Package | In | Out |
|---|---|---|---|
| `spec/` | Spec schema + validator + prompt→spec compiler | words + refs | `SCENE_SPEC.md` (valid) |
| `blender/` | bpy library (collections, materials, cameras, labels, QA) + `build.py` | spec | `.blend` + QA PNGs |
| `web/` | Three.js template + preset JSON | spec | self-contained HTML + snapshot PNG |
| `qa/` | zero-vision asserts (legible, match, no-overlap) | renders | pass/fail + diff |
| `skill/` | `code-to-3d/SKILL.md` + scripts + references | — | installable skill |

Seed material: `blender-mcp-examples` brain session (11 builder scripts),
brain v2 HTML (web template), zero-vision (QA reader).

## 5. Non-goals (0.1.0)

No mesh-gen training, no hosted renderer (self-hosted lenovo covers CI),
no visual editor, no React wrapper, no DocIR-3D bridge.

## 5b. What we're doing different (read: ahujasid + emeryporter, Sep 2026)

Every public Blender MCP sells VERBS: 86 tools, execute-anything, asset
downloads, screenshots you eyeball. Their troubleshooting is "break into
smaller steps, restart both." No spec layer, no determinism, no loop.

We sell OUTCOMES: spec in, verified scene out. The zoo stays hidden behind
~6 verbs. SCENE_SPEC.md + validator is the moat; the closed QA loop
(zero-vision reads renders as text, asserts, rebuilds) is the engine; two
backends from one spec is the reach. One line: they built remote controls
for Blender; we're building the director who knows what to shoot.

Counterweight (do not rebuild): ahujasid's 28k-star asset pipelines (Poly
Haven, Sketchfab, Hunyuan3D). Integrate — their MCP can be our execution
backend under our spec. Compete on the loop, borrow the hands.

## 5c. Backend census (Sep 2026 — verified where stated, prices approx)

Axes: human learning curve vs AGENT affinity (training footprint + format
agents write natively) vs three separate agent paths (MCP / computer-use /
browser-use). Verdicts: RIDE (backend slot), INTEGRATE (file formats only),
WATCH, SKIP, ROUTE AROUND.

```
BACKEND      BORN   PRICE~     POPULARITY      HUMAN   AGENT-   MCP    COMP-   BROWSER  INDUSTRY   VERDICT
                                       CURVE   AFFINITY                      USE
Blender      1994   free      massive/growing  steep   HIGH      RICH   yes    yes      film/indie RIDE (1)
Three.js     2010   free MIT  113k★ 5M dl/wk   gentle  HIGHEST   NATIVE yes    yes      web std    RIDE (2)
Babylon.js   2013   free Ap.  solid #2         moderate MEDIUM   thin   yes    yes      games/web  WATCH
PlayCanvas   2011   free MIT  16k★ niche       moderate LOW      ~none  no     partial  ads/games  SKIP
Godot        2014   free      rising fast      moderate LOW      weak   no     partial  indie      SKIP
Unity        2005   free→$$$  volume leader    steep   LOW       poor   driver* driver*  AAA/mobile INTEGRATE
Unreal       1998   5%>$1M    AAA standard     cliff   LOW       poor   driver* driver*  AAA/film   INTEGRATE
Houdini      1996   $269→$$$  procedural king  cliff   MEDIUM    none   no     no       FX         RESPECT
C4D          1990   ~$1k/yr   motion design    moderate LOW      none   no     no       broadcast  ROUTE AROUND
Maya         1998   ~$1.8k/yr film standard    cliff   LOW       none   no     no       film       ROUTE AROUND
(* driver = heavyweight editor automation only — expensive, fragile, last resort)
```

Reads: ride Blender (only heavyweight with a real MCP story + headless bpy
+ free) and Three.js (agents dream in HTML/JS; HyperFrames proved seekable
rendering). Babylon waits for a paying user. Unity/Unreal/Houdini are met
at the file-format border (FBX, glTF, USD) — never fought head-on. The kill
list is not an engine: seat-licensed, API-less DCC silos die of irrelevance
inside the agent loop, and our exports stay importable by their pipelines
so the door stays open.

## 6. Deliver-or-die acceptance

1. One prompt + refs → spec → `.blend` AND `.html` with zero hand edits.
2. QA loop catches an injected label overlap without human help.
3. Third-party agent installs skill + MCP and builds a novel scene solo.
4. `npm`-style one-command install; Apache 2.0; README design/table pattern.

## 7. Workstreams (parallel)

- A. Scaffold: repo layout, README, CI skeleton, examples migration.
- B. Spec: schema, validator, prompt→spec compiler sketch, skill draft.
- C. Blender lib: generalize builders (collections/materials, cameras/labels/QA).
- D. Web template: generalize brain v2 into spec-driven template + presets.
- E. QA loop: zero-vision asserts wired to renders, `next_qa` as a loop.

Budget to 0.1.0: ~1M tokens, ~8 sessions. Phase B (spec schema) is
load-bearing — everything composes if it's right.
