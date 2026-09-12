# AGENTS.md — working in RealEngine

Standing brief for any agent touching this repo. Read it before the first edit.

## The laws

**Fail closed.** A missing dependency, an unparseable block, an absent OCR
engine: say what is missing and exit non-zero. Never a silent pass, never
`|| true`, never a stub that returns success. This repo's own MCP tools
promise `ok:false` with a named requirement instead of faking a result —
match that everywhere you write code or CI.

**The spec is the contract, and it is pinned.** After drafting, a
`SCENE_SPEC.md` is deterministic: same bytes in, same `build.json` bytes and
the same `sha256` out, on any machine. Golden files in `tests/golden/` pin
it. A deliberate change regenerates the golden in the same commit and says
why in the commit message; an accidental one is a bug, not a golden to chase.

**No Blender and no browser in the default test path.**
`python -m unittest discover -s tests -p 'test_*.py'` must pass on a machine
with neither installed. Optional dependencies are detected and reported,
never assumed — `web/render_views.py` exits 3 and names what's missing, it
does not pretend a render happened.

**LiteLLM first.** The one networked call in the repo is `spec/llm.py`,
reached through `compile_brief`. It goes through the LiteLLM proxy; base URL
and key come from the environment and there is no hardcoded vendor.
`REALENGINE_LLM_STUB` is the offline path the tests use. Without a
configured base URL, drafting fails closed — it does not fall back to some
other provider.

**No secrets in the tree.** No keys in code, tests, fixtures, goldens, or
committed renders. Nothing printed to a transcript.

**CI stays inside the free quota.** `ubuntu-latest` only, no macOS runner,
no self-hosted runner on this public repo. A disabled gate must read as
loudly absent, never as a quiet green — a check that silently stops running
is worse than no check at all.

## Layout

| Dir | What |
|---|---|
| `spec/` | Schema (`SPEC-SCHEMA.md`) + `validate.py` + `scene_spec.py` (md ⇄ JSON, placement, hashing) + `geometry.py` (geometry block → primitive parts) + `compile_brief.py` (prompt → spec) + `llm.py` (the one model call) |
| `web/` | `build_scene.py` (spec → scene), `template_scene.html` (Three.js), `render_views.py` (headless screenshots), plus the legacy slot builder `build_web.py` |
| `blender/` | `ctd_blender` bpy library (collections, materials, `blockout.py`, `primitives.py` tessellation, lighting, cameras) + `build.py` + `run_headless.py` |
| `qa/` | `asserts.py` (`labels_present`, `views_match`, `no_overlap`) + `png_stats.py` (non-black check) + `run_qa.py` (OCR CLI) |
| `mcp/` | The MCP TypeScript server: 6 tools, each running the Python step that owns the job |
| `examples/` | One dir per scene: `SCENE_SPEC.md` + refs + final output |
| `tests/` | `test_all.py` + `golden/` (pinned build JSON, emitted Markdown, hashes) |

## How to verify your change

```bash
# unit tests — no Blender, no browser, must pass on a bare machine
python3 -m unittest discover -s tests -p 'test_*.py'

# spec validity
python3 spec/validate.py examples/desk-lamp/SCENE_SPEC.md

# spec <-> markdown round trip (fixpoint) + deterministic build
python3 spec/scene_spec.py roundtrip examples/desk-lamp/SCENE_SPEC.md
python3 web/build_scene.py examples/desk-lamp/SCENE_SPEC.md --out-dir /tmp/lamp_a
python3 web/build_scene.py examples/desk-lamp/SCENE_SPEC.md --out-dir /tmp/lamp_b
diff -u /tmp/lamp_a/build.json /tmp/lamp_b/build.json   # must be empty

# MCP server
cd mcp && npm ci && npm run build && npm test
```

Heavy steps — headless Blender, Playwright/Chromium renders, `npm` installs —
belong on CI or a build box, not in a fast edit loop. The default test path
above is deliberately cheap so it can run on every change.
