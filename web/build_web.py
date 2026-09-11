#!/usr/bin/env python3
"""Build a standalone Three.js scene HTML from a template + preset.

SPEC BINDINGS (spec/SPEC-SCHEMA.md field names -> slot families):
  Units/axes+envelopes -> {{dim_brain_w/d/h}}, {{dim_head_w/d/h}}
  Palette (hex per region) -> {{palette_<region>}} (bare hex, no prefix;
    template adds "#" or "0x"), {{palette_l1..l5}}, {{palette_flow_*}}
  Collections tree -> {{layer_<group>_name}} (HUD layer toggles)
  Cameras (CAM_* entries) -> {{cam_<key>_desc/pos/target/explode/button}},
    {{cam_toast_default}}
  Build order -> embodied in template geometry sequence (structural, not a slot)
  Priority rule -> structural comment in template (not a slot)
  Exact label strings -> {{labeldef_*}}, {{stack_label_*}}, {{legend_name_*}},
    {{anatomy_<KEY>_name/code/desc/role}}, {{loop_step_1..7}},
    {{inspector_default_*}}, {{scene_heading/subtitle/title_tag}},
    {{snapshot_filename}}

Usage:
  python3 build_web.py <preset.json> <template.html> <out.html>

Rules (fail loudly, exit 1 on stderr):
  - every {{slot}} in the template must have a key in the preset
  - after substitution no "{{" or "}}" may survive in the output
Stdlib only.
"""

import json
import re
import sys

SLOT_RE = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")


def fail(msg):
    print(f"build_web: ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def main(argv):
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    preset_path, template_path, out_path = argv[1], argv[2], argv[3]

    try:
        with open(preset_path, "r", encoding="utf-8") as f:
            preset = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        fail(f"cannot read preset {preset_path}: {e}")
    if not isinstance(preset, dict):
        fail(f"preset {preset_path} must be a JSON object")

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
    except OSError as e:
        fail(f"cannot read template {template_path}: {e}")

    slots = sorted(set(SLOT_RE.findall(template)))
    if not slots:
        fail("template contains no {{slots}} — refusing to copy a file blindly")
    missing = [s for s in slots if s not in preset]
    if missing:
        fail(f"{len(missing)} unbound slot(s): {', '.join(missing)}")

    unused = sorted(k for k in preset if k.startswith("_") is False and k not in slots)
    if unused:
        print(f"build_web: WARN: {len(unused)} unused preset key(s): "
              f"{', '.join(unused)}", file=sys.stderr)

    def sub(m):
        v = preset[m.group(1)]
        if isinstance(v, bool):
            return "true" if v else "false"
        return str(v)

    out = SLOT_RE.sub(sub, template)

    survivors = re.findall(r"\{\{|\}\}", out)
    if survivors:
        idx = out.find("{{")
        if idx < 0:
            idx = out.find("}}")
        fail(f"surviving '{{{{...}}}}' in output near: ...{out[max(0, idx - 60):idx + 60]!r}...")

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(out)
    except OSError as e:
        fail(f"cannot write {out_path}: {e}")

    print(f"build_web: OK: {len(slots)} slots bound -> {out_path}")


if __name__ == "__main__":
    main(sys.argv)
