# Build plan — subagent fleet, coordinator/chief-architect model

## Command

Coordinator (this session): owns the spec, dispatches workstreams, verifies
every claim independently, integrates. Never takes a subagent's word on a
green check — re-runs the receipt.

## Fleet rules (non-negotiable in every brief)

1. Report back to coordinator in ONE final message. Never spawn subagents,
   never message other sessions.
2. Touch only your assigned subtree. Seed repos are read-only.
3. Every deliverable carries its own receipt (test output, bytes, counts).
4. No heavy compute on the MacBook — Blender runs and renders go to lenovo;
   node/python checks stay local.
5. `FINAL MESSAGE FORMAT` is part of every brief and is enforced.

## Waves

| Wave | Lanes (parallel) | Gate to next wave |
|---|---|---|
| 0. Done | A scaffold, B spec+skill, C blender lib | Coordinator verify (compile, validator, grep) |
| 1. Next | D web template (spec-driven Three.js), E QA loop (zero-vision asserts) | Brain rebuild end-to-end with zero hand edits |
| 2. Then | F prompt→spec compiler, G MCP tiny surface | Third-party agent builds a novel scene solo |
| 3. Ship | H skill publish, docs pass, OIDC release flow | 0.1.0 tag, CI green, registry live |

## Token budgets

Wave 0: ~150k (spent). Wave 1: ~400k. Wave 2: ~300k. Wave 3: ~100k.
Total ~1M to 0.1.0. B (spec schema) is load-bearing — D and E compose
against it; C's geometry stubs resolve once B names meshes.

## Blocked on human (not the fleet)

- GitHub repo creation (`code-to-3d`, crew) — token lacks scope.
- npm Trusted Publisher — done for zero-vision; repeat per package.
- Human Gates 1+2 on every build: spec approval, the eye.
