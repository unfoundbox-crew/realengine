#!/usr/bin/env python3
"""SCENE_SPEC.md <-> scene JSON round trip. Stdlib only, deterministic.

This is the missing link the architecture doc called out: `SCENE_SPEC.md`
is the contract humans read, but `blender/build.py` and `web/build_web.py`
consume JSON. Nothing converted one into the other. This module does.

Three layers, each a pure function:

1. ``parse_spec(text) -> scene``     Markdown contract -> declarative dict.
2. ``emit_spec(scene) -> text``      Declarative dict -> canonical Markdown
                                     (passes ``spec/validate.py``, and
                                     ``parse_spec`` of it returns the same
                                     dict -- a fixpoint, not a byte copy of
                                     the hand-written original).
3. ``to_build_json(scene) -> build`` Declarative dict -> the build dict
                                     ``blender/build.py`` already consumes
                                     (``scene``/``collections``/``palette``/
                                     ``cameras``/``views``) plus ``objects``
                                     and ``labels`` for the web backend.
                                     Placement is computed here, never
                                     guessed: a deterministic grid blockout.

``build_hash(build)`` pins the result: sha256 over the canonical JSON. The
same spec bytes always produce the same hash on any machine.

CLI::

    python3 spec/scene_spec.py parse     <SCENE_SPEC.md> [-o scene.json]
    python3 spec/scene_spec.py emit      <scene.json>    [-o SCENE_SPEC.md]
    python3 spec/scene_spec.py build     <SCENE_SPEC.md> [-o build.json]
    python3 spec/scene_spec.py hash      <SCENE_SPEC.md>
    python3 spec/scene_spec.py roundtrip <SCENE_SPEC.md>

Parse rules are normative and documented in ``spec/SPEC-SCHEMA.md``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys

SPEC_MODULE_VERSION = "0.2.0"

# ---------------------------------------------------------------- primitives

HEADING_RE = re.compile(r"^(#{1,3})\s+(.*?)\s*$")
FENCE_RE = re.compile(r"```[A-Za-z0-9]*\n(.*?)```", re.S)
BULLET_RE = re.compile(r"^\s*[-*]\s+(.*?)\s*$")
# Longest-first so #E8EEF3 never matches as #E8E, and no hex digit may follow.
_HEX = r"(?:[0-9A-Fa-f]{8}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})(?![0-9A-Fa-f])"
HEX_RE = re.compile(r"`?#(" + _HEX + r")`?")
BULLET_HEX_RE = re.compile(
    r"^(?P<name>[^:`#]+?)\s*[:—-]?\s*`?#(?P<hex>" + _HEX + r")`?"
    r"(?:\s+alpha\s+(?P<alpha>\d*\.?\d+))?"
    r"(?:\s+roughness\s+(?P<rough>\d*\.?\d+))?\s*$"
)
MATERIAL_HEX_RE = re.compile(r"(?i)material\s*[:=]\s*#(" + _HEX + r")")
OBJECT_NAME_RE = re.compile(r"\b([A-Z]{2,})_([A-Za-z0-9][A-Za-z0-9_]*)\b")
CAM_RE = re.compile(r"\b(CAM_[A-Za-z0-9_]+)\b")
NUMBERED_RE = re.compile(r"^\s*(\d+)\s+(\S.*?)\s*$")
TRIPLE_DIM_RE = re.compile(
    r"~?\s*(\d+(?:\.\d+)?)\s*[×x]\s*(\d+(?:\.\d+)?)\s*[×x]\s*"
    r"(\d+(?:\.\d+)?)\s*(mm|m)\b"
)
SINGLE_DIM_RE = re.compile(r"~\s*(\d+(?:\.\d+)?)\s*(mm|m)\b")
RES_RE = re.compile(r"(\d{3,5})\s*[×x]\s*(\d{3,5})")
ALPHA_RE = re.compile(r"(?i)\balpha\s*(\d*\.?\d+)")
ROUGH_RE = re.compile(r"(?i)\broughness\s*(\d*\.?\d+)")
PREFIX_MAP_RE = re.compile(
    r"^([A-Z]{2,}_)\s*(?:->|=>|→)\s*([0-9A-Za-z_]+)\s*$"
)

# Prefix stem -> collection-name token. Documented default; a spec may
# override any row with an explicit "PREFIX_ -> COLLECTION" line in its
# Naming section.
PREFIX_SYNONYMS = {
    "CTX": "CORTEX",
    "SUB": "SUBCORTICAL",
    "CTRL": "CONTROL",
    "FLOW": "FLOW",
    "LAYER": "LAYER",
    "LABEL": "LABELS",
    "LEGEND": "LEGENDS",
    "CAM": "CAMERAS",
    "LIGHT": "LIGHTS",
    "HEAD": "HEAD",
    "REF": "REFERENCE",
}

DEFAULT_PRIORITY = ("scene_spec.md > orthographic views > master perspective"
                    " > detail aesthetics")

# Deterministic neutral ramp for objects with no palette entry of their own.
FALLBACK_RAMP = ["#C8D2DC", "#B9C6D2", "#AAB9C8", "#9BADBE", "#8CA1B4"]

DEFAULT_MASTER_RES = (1600, 900)
DEFAULT_ORTHO_RES = (1200, 1200)


def _debacktick(s):
    return s.replace("`", "")


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _round(x, nd=6):
    """Round for JSON stability: -0.0 and 1e-17 must not reach the file."""
    v = round(float(x), nd)
    return 0.0 if v == 0 else v


def _to_metres(value, unit):
    return float(value) / 1000.0 if unit == "mm" else float(value)


def split_sections(text):
    """Return [(level, heading, body)] in document order; preamble is level 0."""
    lines = text.splitlines()
    sections = [(0, "", [])]
    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            sections.append((len(m.group(1)), m.group(2), []))
        else:
            sections[-1][2].append(line)
    return [(lvl, head, "\n".join(body)) for lvl, head, body in sections]


def find_section(sections, pattern):
    """Body of the first section whose heading matches ``pattern``."""
    rx = re.compile(pattern, re.I)
    for _lvl, head, body in sections:
        if rx.search(head):
            return body
    return ""


def bullets(body):
    return [m.group(1) for m in (BULLET_RE.match(l) for l in body.splitlines()) if m]


def fences(body):
    return [m.group(1) for m in FENCE_RE.finditer(body)]


# -------------------------------------------------------------------- parse


def _parse_title(text, sections):
    for lvl, head, _body in sections:
        if lvl == 1 and head.strip():
            return head.strip()
    for lvl, head, _body in sections:
        if head.strip():
            return head.strip()
    return "Untitled Scene"


def _scene_name(title):
    stem = re.sub(r"(?i)\s*scene\s*spec\s*$", "", title).strip() or title
    slug = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_")
    return slug or "CTD_SCENE"


def _parse_units(sections):
    body = find_section(sections, r"units")
    flat = _debacktick(body)
    units = {
        "system": "METRIC" if re.search(r"(?i)metric", flat) else "NONE",
        "up": (re.search(r"(?i)\b([XYZ])\s*up\b", flat).group(1).upper()
               if re.search(r"(?i)\b([XYZ])\s*up\b", flat) else "Z"),
        "envelopes": {},
        "tolerances": [],
        "notes": [],
    }
    for b in bullets(flat):
        units["notes"].append(b)
        if "±" in b:
            units["tolerances"].append(b)
        m = re.match(r"(?i)^(?P<name>[A-Za-z][A-Za-z0-9 _-]*?)\s+envelope\s*[:=]\s*(?P<rest>.*)$", b)
        if m:
            dim = TRIPLE_DIM_RE.search(m.group("rest"))
            if dim:
                unit = dim.group(4)
                units["envelopes"][_norm(m.group("name"))] = [
                    _round(_to_metres(dim.group(i), unit)) for i in (1, 2, 3)
                ]
    return units


def _parse_palette(sections):
    """Named hex colours from every section, in document order.

    Two forms enter the palette:
      * a bullet carrying a name and a hex  (``- Frontal `#7EA6FF```)
      * a ``material: #HEX`` line, named after its section heading
    A section-level ``alpha``/``roughness`` line applies to the entries
    parsed inside that section (lower bound of a range).
    """
    palette = {}
    for _lvl, head, body in sections:
        flat = _debacktick(body)
        am = ALPHA_RE.search(flat)
        rm = ROUGH_RE.search(flat)
        alpha = _round(float(am.group(1))) if am else 1.0
        rough = _round(float(rm.group(1))) if rm else 0.45
        for b in bullets(body):
            bm = BULLET_HEX_RE.match(b.strip())
            if not bm:
                continue
            name = bm.group("name").strip().strip("`").strip()
            if not name:
                continue
            palette.setdefault(name, {
                "hex": "#" + bm.group("hex").upper(),
                "alpha": (_round(float(bm.group("alpha")))
                          if bm.group("alpha") else alpha),
                "roughness": (_round(float(bm.group("rough")))
                              if bm.group("rough") else rough),
            })
        mm = MATERIAL_HEX_RE.search(flat)
        if mm and head.strip():
            palette.setdefault(head.strip(), {
                "hex": "#" + mm.group(1).upper(),
                "alpha": alpha,
                "roughness": rough,
            })
    return palette


def _parse_collections(sections):
    body = find_section(sections, r"collections")
    names = []
    blocks = fences(body) or [body]
    for line in blocks[0].splitlines():
        cleaned = re.sub(r"^[\s─-╿|`+\-]*", "", line).strip()
        cleaned = cleaned.strip("`").strip()
        if not cleaned or cleaned.upper() == "SCENE":
            continue
        token = cleaned.split()[0]
        if re.match(r"^[0-9A-Za-z_]+$", token) and token not in names:
            names.append(token)
    return names


def _parse_prefix_overrides(sections):
    body = _debacktick(find_section(sections, r"naming"))
    out = {}
    for line in body.splitlines():
        m = PREFIX_MAP_RE.match(line.strip())
        if m:
            out[m.group(1).rstrip("_").upper()] = m.group(2)
    return out


def _collection_for(prefix, collections, overrides):
    if prefix in overrides:
        return overrides[prefix]
    token = PREFIX_SYNONYMS.get(prefix, prefix)
    for name in collections:
        if token in name.upper():
            return name
    for name in collections:
        if prefix in name.upper():
            return name
    return collections[0] if collections else "00_SCENE"


def _parse_labels(sections):
    body = find_section(sections, r"label")
    out = []
    for b in bullets(body):
        flat = _debacktick(b).strip()
        parts = re.split(r"\s+[—–]\s+|\s+--\s+", flat, maxsplit=1)
        name = parts[0].strip().rstrip(":").strip()
        if not name:
            continue
        out.append({
            "name": name,
            "subtitle": parts[1].strip() if len(parts) > 1 else "",
        })
    return out


def _parse_objects(sections, collections, labels):
    body = find_section(sections, r"naming")
    overrides = _parse_prefix_overrides(sections)
    seen = []
    for m in OBJECT_NAME_RE.finditer(_debacktick(body)):
        name = "%s_%s" % (m.group(1), m.group(2))
        if name not in seen:
            seen.append(name)

    sizes = _parse_sizes(sections)
    objects = []
    for idx, name in enumerate(seen):
        prefix, suffix = name.split("_", 1)
        label = _best_label(suffix, labels)
        objects.append({
            "name": name,
            "prefix": prefix,
            "collection": _collection_for(prefix, collections, overrides),
            "size_mm": (sizes.get(_norm(name)) or sizes.get(_norm(suffix))
                        or _default_size_mm(idx)),
            "label": label["name"] if label else suffix,
            "subtitle": label["subtitle"] if label else "",
        })
    return objects


def _default_size_mm(idx):
    """Deterministic fallback volume for objects the spec never dimensions."""
    base = 30.0 + (idx % 3) * 4.0
    return [_round(base, 3), _round(base * 0.8, 3), _round(base * 0.8, 3)]


def _parse_sizes(sections):
    """{normalized name: [w, d, h] mm} from any dimensioned bullet."""
    out = {}
    for _lvl, _head, body in sections:
        for b in bullets(body):
            flat = _debacktick(b).strip()
            m = re.match(r"^(?P<name>[A-Za-z][A-Za-z0-9 _/-]*?)\s*[:—-]\s*(?P<rest>.*)$", flat)
            if not m:
                continue
            key = _norm(m.group("name"))
            if not key:
                continue
            rest = m.group("rest")
            t = TRIPLE_DIM_RE.search(rest)
            if t:
                unit = t.group(4)
                mm = [_round(_to_metres(t.group(i), unit) * 1000.0, 3) for i in (1, 2, 3)]
                out.setdefault(key, mm)
                continue
            s = SINGLE_DIM_RE.search(rest)
            if s:
                v = _round(_to_metres(s.group(1), s.group(2)) * 1000.0, 3)
                out.setdefault(key, [v, v, v])
    return out


def _best_label(suffix, labels):
    """Longest label whose normalized text contains the object's suffix."""
    key = _norm(suffix)
    best = None
    for lab in labels:
        ln = _norm(lab["name"])
        if key and (key in ln or ln in key):
            if best is None or len(ln) > len(_norm(best["name"])):
                best = lab
    return best


def _parse_cameras(sections):
    body = find_section(sections, r"cameras?")
    out = []
    seen = set()
    for line in body.splitlines():
        flat = _debacktick(line)
        for m in CAM_RE.finditer(flat):
            name = m.group(1)
            if name in seen:
                continue
            seen.add(name)
            rest = flat[m.end():].strip()
            rest = re.sub(r"^[\s—–:-]+", "", rest).strip()
            out.append({"name": name, "desc": rest})
    return out


def _parse_build_order(sections):
    body = find_section(sections, r"build order")
    blocks = fences(body) or [body]
    steps = []
    for line in blocks[0].splitlines():
        m = NUMBERED_RE.match(_debacktick(line))
        if m:
            steps.append(m.group(2).strip())
    return steps


def _parse_priority(text):
    """The conflict rule: same line as "conflict priority", else the next one."""
    lines = _debacktick(text).splitlines()
    for i, line in enumerate(lines):
        if not re.search(r"(?i)conflict priority", line):
            continue
        val = re.sub(r"(?i)^.*conflict priority\s*[:—-]*\s*", "", line).strip()
        if val:
            return val
        for nxt in lines[i + 1:]:
            if nxt.strip():
                return nxt.strip()
        return ""
    for line in lines:
        if re.search(r"(?i)priorit", line) and not line.lstrip().startswith("#"):
            return line.strip()
    return ""


def _parse_render(sections):
    body = _debacktick(find_section(sections, r"render"))
    master, ortho = DEFAULT_MASTER_RES, DEFAULT_ORTHO_RES
    for b in bullets(body):
        res = RES_RE.search(b)
        if not res:
            continue
        pair = (int(res.group(1)), int(res.group(2)))
        if re.search(r"(?i)master", b):
            master = pair
        elif re.search(r"(?i)ortho", b):
            ortho = pair
    engine = "CYCLES" if re.search(r"(?i)cycles", body) else "BLENDER_EEVEE_NEXT"
    bg = HEX_RE.search(find_section(sections, r"lighting") or "")
    return {
        "master_res": list(master),
        "ortho_res": list(ortho),
        "engine": engine,
        "background": ("#" + bg.group(1).upper()) if bg else "#F8FAFC",
    }


def parse_spec(text):
    """Parse a SCENE_SPEC.md into the declarative scene dict."""
    sections = split_sections(text)
    title = _parse_title(text, sections)
    collections = _parse_collections(sections)
    labels = _parse_labels(sections)
    scene = {
        "spec_module_version": SPEC_MODULE_VERSION,
        "title": title,
        "scene": _scene_name(title),
        "units": _parse_units(sections),
        "palette": _parse_palette(sections),
        "collections": collections,
        "objects": _parse_objects(sections, collections, labels),
        "cameras": _parse_cameras(sections),
        "labels": labels,
        "build_order": _parse_build_order(sections),
        "priority": _parse_priority(text),
        "render": _parse_render(sections),
    }
    return scene


def parse_spec_file(path):
    with open(path, encoding="utf-8") as f:
        return parse_spec(f.read())


# --------------------------------------------------------------------- emit


def emit_spec(scene):
    """Emit a canonical SCENE_SPEC.md. A fixpoint under ``parse_spec``.

    Not a byte copy of a hand-written spec: the same *meaning*, in the
    canonical shape, such that ``parse_spec(emit_spec(s)) == s``.
    """
    u = scene["units"]
    out = []
    w = out.append
    w("# %s" % scene["title"])
    w("")
    # Wording note: the preamble must not contain the words "build order" --
    # spec/validate.py slices that section from the FIRST match in the file.
    w("Generated by spec/scene_spec.py v%s. This file is authoritative for"
      % scene.get("spec_module_version", SPEC_MODULE_VERSION))
    w("semantics, naming, dimensions, hierarchy, and the numbered sequence below.")
    w("")
    w("## Units and coordinates")
    w("")
    notes = u.get("notes") or _synth_unit_notes(u)
    for note in notes:
        w("- %s" % note)
    w("")
    w("## Palette")
    w("")
    for name in sorted(scene["palette"]):
        p = scene["palette"][name]
        w("- %s `%s` alpha %s roughness %s"
          % (name, p["hex"], _fmt(p["alpha"]), _fmt(p["roughness"])))
    w("")
    w("## Collections")
    w("")
    w("```text")
    w("SCENE")
    for name in scene["collections"]:
        w("├── %s" % name)
    w("```")
    w("")
    w("## Naming")
    w("")
    w("Prefix to collection:")
    w("")
    w("```text")
    for prefix, coll in sorted(_prefix_table(scene).items()):
        w("%s_ -> %s" % (prefix, coll))
    w("```")
    w("")
    w("Required objects:")
    w("")
    w("```text")
    for obj in scene["objects"]:
        w("%s" % obj["name"])
    w("```")
    w("")
    w("## Object dimensions")
    w("")
    for obj in scene["objects"]:
        w("- %s: `%s mm`" % (obj["name"],
                             " × ".join(_fmt(d) for d in obj["size_mm"])))
    w("")
    w("## Cameras")
    w("")
    for cam in scene["cameras"]:
        w("- `%s`%s" % (cam["name"],
                        (" — %s" % cam["desc"]) if cam["desc"] else ""))
    w("")
    w("## Functional labels")
    w("")
    for lab in scene["labels"]:
        w("- %s%s" % (lab["name"],
                      (" — %s" % lab["subtitle"]) if lab["subtitle"] else ""))
    w("")
    w("## Render")
    w("")
    w("- master `%d×%d`" % tuple(scene["render"]["master_res"]))
    w("- orthographic refs `%d×%d`" % tuple(scene["render"]["ortho_res"]))
    w("- engine %s" % ("Cycles" if scene["render"]["engine"] == "CYCLES" else "Eevee"))
    w("")
    w("## Lighting")
    w("")
    w("Background `%s`; large soft key, soft fill, no bloom or volumetrics."
      % scene["render"]["background"])
    w("")
    w("## Deterministic build order")
    w("")
    w("```text")
    for i, step in enumerate(scene["build_order"], 1):
        w("%02d %s" % (i, step))
    w("```")
    w("")
    w("## Priority")
    w("")
    w("Conflict priority: `%s`" % (scene["priority"] or DEFAULT_PRIORITY))
    w("")
    return "\n".join(out)


def _synth_unit_notes(u):
    """Unit bullets for a scene dict that never came from Markdown."""
    notes = ["%s units; 1 unit = 1 meter"
             % ("Metric" if u.get("system") == "METRIC" else "Generic"),
             "%s up" % u.get("up", "Z")]
    for name in sorted(u.get("envelopes", {})):
        dims = u["envelopes"][name]
        notes.append("%s envelope: %s m"
                     % (name.capitalize(), " × ".join(_fmt(d) for d in dims)))
    notes.extend(u.get("tolerances", []))
    return notes


def _fmt(x):
    """Shortest stable decimal form: 0.15 not 0.150000, 35 not 35.0."""
    f = float(x)
    if f == int(f):
        return str(int(f))
    return ("%.6f" % f).rstrip("0").rstrip(".")


def _prefix_table(scene):
    return {obj["prefix"]: obj["collection"] for obj in scene["objects"]}


# ---------------------------------------------------------------- build json


def _normalize_dir(vec):
    n = math.sqrt(sum(c * c for c in vec)) or 1.0
    return [c / n for c in vec]


CAMERA_RULES = [
    # (keyword, direction, distance factor, ortho)
    ("topdown", (0.0, -0.001, 1.0), 2.6, True),
    ("top", (0.0, -0.001, 1.0), 2.6, True),
    ("left", (-1.0, 0.0, 0.12), 2.6, True),
    ("right", (1.0, 0.0, 0.12), 2.6, True),
    ("front", (0.0, -1.0, 0.12), 2.6, True),
    ("back", (0.0, 1.0, 0.12), 2.6, True),
    ("rear", (0.0, 1.0, 0.12), 2.6, True),
    ("exploded", (-0.7, -0.7, 0.7), 3.1, False),
    ("detail", (-0.35, -0.9, 0.28), 1.5, False),
]
DEFAULT_CAMERA_RULE = ((-0.6, -0.8, 0.45), 2.4, False)


def _camera_placement(name, extent, center):
    low = name.lower()
    direction, dist_factor, ortho = DEFAULT_CAMERA_RULE
    for key, d, f, o in CAMERA_RULES:
        if key in low:
            direction, dist_factor, ortho = d, f, o
            break
    if "ortho" not in low and ortho and "top" not in low:
        # a named axis view without "ortho" stays perspective
        ortho = False
    unit = _normalize_dir(direction)
    dist = dist_factor * max(extent) if max(extent) else 1.0
    pos = [_round(center[i] + unit[i] * dist) for i in range(3)]
    return pos, ortho, _round(2.3 * max(extent) or 1.0)


def to_build_json(scene):
    """Derive the build dict the backends consume. Pure and deterministic.

    Layout is a grid blockout: one named proxy volume per named object,
    ordered by (collection index, spec order), palette-coloured, labelled.
    It is a faithful rendering of what the spec *states* -- not invented
    anatomy.
    """
    collections = list(scene["collections"])
    col_index = {name: i for i, name in enumerate(collections)}
    objects = sorted(
        enumerate(scene["objects"]),
        key=lambda pair: (col_index.get(pair[1]["collection"], len(collections)),
                          pair[0]),
    )

    sizes_m = []
    for _i, obj in objects:
        sizes_m.append([max(_to_metres(d, "mm"), 0.001) for d in obj["size_mm"]])

    # Packed grid: each column is as wide as its widest object and each row
    # as deep as its deepest, so a 1.2 m bench next to a 60 mm bulb does not
    # scatter everything across a giant field. Gap scales with the median
    # object, not the largest.
    count = len(objects) or 1
    cols = max(1, int(math.ceil(math.sqrt(count))))
    rows = max(1, int(math.ceil(count / float(cols))))
    spread = sorted(max(s) for s in sizes_m) or [0.05]
    gap = 0.45 * spread[len(spread) // 2]

    col_w = [0.0] * cols
    row_d = [0.0] * rows
    for slot, size in enumerate(sizes_m):
        r, c = divmod(slot, cols)
        col_w[c] = max(col_w[c], size[0])
        row_d[r] = max(row_d[r], size[1])

    col_x, x_cursor = [], 0.0
    for w in col_w:
        col_x.append(x_cursor + w / 2.0)
        x_cursor += w + gap
    total_w = max(x_cursor - gap, 0.001)
    col_x = [x - total_w / 2.0 for x in col_x]

    row_y, y_cursor = [], 0.0
    for d in row_d:
        row_y.append(y_cursor + d / 2.0)
        y_cursor += d + gap
    total_d = max(y_cursor - gap, 0.001)
    row_y = [total_d / 2.0 - y for y in row_y]

    placed = []
    for slot, ((_i, obj), size) in enumerate(zip(objects, sizes_m)):
        r, c = divmod(slot, cols)
        pal = _palette_for(obj, scene)
        placed.append({
            "name": obj["name"],
            "collection": obj["collection"],
            "palette": pal[0],
            "hex": pal[1]["hex"],
            "alpha": pal[1]["alpha"],
            "roughness": pal[1]["roughness"],
            "pos": [_round(col_x[c]), _round(row_y[r]), _round(size[2] / 2.0)],
            "size_m": [_round(s) for s in size],
            "label": obj["label"],
            "subtitle": obj["subtitle"],
        })

    half_x = total_w / 2.0 or 0.5
    half_y = total_d / 2.0 or 0.5
    half_z = (max([s[2] for s in sizes_m] or [0.1])) or 0.1
    extent = [_round(half_x), _round(half_y), _round(max(half_z, 0.05))]
    center = [0.0, 0.0, _round(half_z / 2.0)]

    cameras = []
    for cam in scene["cameras"]:
        pos, ortho, ortho_scale = _camera_placement(cam["name"], extent, center)
        cameras.append({
            "name": cam["name"],
            "desc": cam["desc"],
            "pos": pos,
            "target": center,
            "lens": 62.0,
            "ortho": ortho,
            "ortho_scale": ortho_scale,
        })

    master = scene["render"]["master_res"]
    ortho_res = scene["render"]["ortho_res"]
    views = []
    for cam in cameras:
        res = ortho_res if cam["ortho"] else master
        views.append({
            "name": cam["name"],
            "camera": cam["name"],
            "output": "%s.png" % cam["name"],
            "res_x": res[0],
            "res_y": res[1],
        })

    return {
        "spec_module_version": scene.get("spec_module_version", SPEC_MODULE_VERSION),
        "scene": scene["scene"],
        "title": scene["title"],
        "units": scene["units"],
        "collections": collections,
        "palette": scene["palette"],
        "objects": placed,
        "cameras": cameras,
        "views": views,
        "labels": scene["labels"],
        "build_order": scene["build_order"],
        "priority": scene["priority"],
        "render": scene["render"],
        "extent": extent,
        "center": center,
    }


def _palette_for(obj, scene):
    """Palette entry for an object: exact suffix match, else neutral ramp."""
    suffix = obj["name"].split("_", 1)[1]
    keys = sorted(scene["palette"])
    for key in keys:
        if _norm(key) == _norm(suffix):
            return key, scene["palette"][key]
    for key in keys:
        if _norm(key) and _norm(key) in _norm(suffix):
            return key, scene["palette"][key]
    idx = sum(ord(ch) for ch in obj["name"]) % len(FALLBACK_RAMP)
    return ("_neutral%d" % idx, {
        "hex": FALLBACK_RAMP[idx], "alpha": 1.0, "roughness": 0.45})


# --------------------------------------------------------------------- hash


def canonical_json(obj):
    """Canonical JSON text: sorted keys, tight separators, trailing newline."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False) + "\n"


def build_hash(build):
    """sha256 of the canonical build JSON. The pin."""
    return hashlib.sha256(canonical_json(build).encode("utf-8")).hexdigest()


def md_hash(text):
    """sha256 of the spec Markdown bytes."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compile_spec(text):
    """Markdown -> {scene, build, build_sha256, spec_sha256}. No I/O, no net."""
    scene = parse_spec(text)
    build = to_build_json(scene)
    return {
        "scene": scene,
        "build": build,
        "build_sha256": build_hash(build),
        "spec_sha256": md_hash(text),
    }


# ---------------------------------------------------------------------- CLI


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command",
                    choices=["parse", "emit", "build", "hash", "roundtrip"])
    ap.add_argument("path")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args(argv)

    if args.command == "emit":
        scene = json.loads(_read(args.path))
        if "build" in scene and "scene" in scene and isinstance(scene["scene"], dict):
            scene = scene["scene"]
        text = emit_spec(scene)
        if args.out:
            _write(args.out, text)
            print("emit: %s" % args.out)
        else:
            sys.stdout.write(text)
        return 0

    text = _read(args.path)
    result = compile_spec(text)

    if args.command == "parse":
        payload = canonical_json(result["scene"])
    elif args.command == "build":
        payload = canonical_json(result["build"])
    elif args.command == "hash":
        print("build_sha256 %s" % result["build_sha256"])
        print("spec_sha256  %s" % result["spec_sha256"])
        return 0
    else:  # roundtrip
        again = parse_spec(emit_spec(result["scene"]))
        ok = canonical_json(again) == canonical_json(result["scene"])
        third = parse_spec(emit_spec(again))
        stable = canonical_json(third) == canonical_json(again)
        print("roundtrip %s (fixpoint=%s stable=%s objects=%d cameras=%d)"
              % ("PASS" if ok and stable else "FAIL", ok, stable,
                 len(result["scene"]["objects"]), len(result["scene"]["cameras"])))
        return 0 if (ok and stable) else 1

    if args.out:
        _write(args.out, payload)
        print("%s: %s (%d bytes)" % (args.command, args.out, len(payload)))
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
