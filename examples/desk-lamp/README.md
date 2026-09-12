# Desk lamp — the second example

A hand-written `SCENE_SPEC.md` for a subject that is not a brain. It exists
to prove the pipeline is generic: the same parser, the same build JSON, the
same two backends.

```bash
python3 spec/validate.py examples/desk-lamp/SCENE_SPEC.md
python3 spec/scene_spec.py roundtrip examples/desk-lamp/SCENE_SPEC.md
python3 web/build_scene.py examples/desk-lamp/SCENE_SPEC.md --out-dir out/lamp
open out/lamp/scene.html
```

What you get is a **blockout**: one named proxy volume per named object in
the spec, at its stated dimensions, in its palette colour, labelled, under
the spec's own cameras. Not a modelled lamp — the spec does not describe
joint angles or profiles, so the builder does not invent them.

Rendered and OCR-checked locally (Chromium via Playwright, zero-vision
`apple-vision`): 4 views, `CAM_LeftOrthographic` passes every label; the
other three miss labels that genuinely fall behind other volumes or outside
the crop. That is the gate working, not a bug.
