# examples/

One directory per scene. Every example carries the same contract:

```
examples/<name>/
  SKILL.md          # skill: what it builds, run order, done criteria
  SCENE_SPEC.md     # authoritative semantics (or TASK.md + manifest.json)
  0N_*.py           # builders, numbered in build order
  0N_*.png          # reference views the QA loop matches
  final/            # outputs: .blend + QA renders (regenerable)
```

Rules: builders take paths as arguments (no absolute paths), every named
structure stays a separate object, deviations from spec are logged, never
silent. New examples copy this shape — the skill is what makes them
agent-runnable, not just human-readable.
