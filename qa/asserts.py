"""Machine half of the code-to-3d QA gate (Wave 1, lane E).

Thesis (TECH-DESIGN.md section 4): machines check (legible, match,
no-overlap), the human eye judges taste. This module is the machine half.

Three asserts:

- labels_present: OCR a render via zero-vision, pass iff every expected
  label appears (case-insensitive substring). Catches missing/illegible
  labels without a human looking.
- views_match: pair PNGs across two render dirs by filename and compare
  pixel dimensions via a minimal PNG IHDR reader (stdlib only, no PIL).
  Dimension check only -- pixel diffing is a later wave.
- no_overlap: real since this wave. Part-wise AABB intersection between the
  named objects of a build, tolerance taken from the spec's own placement
  tolerance. Also accepts flat pixel boxes for the 2D label case.

Stdlib only.
"""

import json
import os
import re
import shutil
import struct
import subprocess
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "spec"))

import geometry as geometry_mod  # noqa: E402

# zero-vision ships bins named zrv / zrv-mcp / snap.
# Prefer local `zrv ocr` if present in PATH to avoid network roundtrips.
# Override with ZERO_VISION_CMD as a colon-separated argv, e.g. "zrv:ocr".
_default_cmd = "zrv:ocr" if shutil.which("zrv") else "npx:-y:-p:zero-vision:zrv:ocr"
OCR_CMD = os.environ.get("ZERO_VISION_CMD", _default_cmd).split(":")
OCR_ENGINE = os.environ.get("ZERO_VISION_ENGINE", "tesseract")


def ocr_text(png):
    """Run zero-vision OCR on a PNG, return stdout text (may be garbled).

    Raises RuntimeError if the OCR subprocess itself fails.
    """
    cmd = list(OCR_CMD) + [png, "--engine", OCR_ENGINE]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("OCR timed out for %s" % png) from e
    except OSError as e:
        raise RuntimeError("could not launch OCR (%s); is npx/network available?" % e) from e
    if proc.returncode != 0:
        raise RuntimeError("OCR failed for %s: %s" % (png, proc.stderr.strip()[-500:]))
    return proc.stdout


def labels_present(png, expected_labels):
    """Pass iff EVERY expected label appears in the OCR text (case-insensitive).

    Returns (ok, missing, text): ok is True when nothing is missing,
    missing lists the labels not found, text is the raw OCR output.
    """
    text = ocr_text(png)
    lowered = text.lower()
    missing = [label for label in expected_labels if label.lower() not in lowered]
    return (not missing, missing, text)


def png_size(path):
    """Read (width, height) from a PNG's IHDR chunk. No PIL, stdlib only."""
    with open(path, "rb") as f:
        header = f.read(33)
    if len(header) < 33 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG: %s" % path)
    # After the 8-byte signature: 4-byte length, 4-byte type ("IHDR"),
    # then width + height as big-endian uint32.
    length, ctype = struct.unpack(">I4s", header[8:16])
    if ctype != b"IHDR" or length < 13:
        raise ValueError("missing IHDR: %s" % path)
    width, height = struct.unpack(">II", header[16:24])
    return (width, height)


def views_match(dir_a, dir_b):
    """Pair PNGs across two dirs by filename, compare pixel dimensions.

    Returns a list of (name, size_a, size_b, match) where sizes are
    (w, h) tuples or None when the file is absent/unreadable, and match
    is True only when both sides read and agree. Dimension check only --
    a full pixel diff is a later wave, not this function.
    """
    def pngs(d):
        return {f for f in os.listdir(d) if f.lower().endswith(".png")}

    rows = []
    for name in sorted(pngs(dir_a) | pngs(dir_b)):
        try:
            size_a = png_size(os.path.join(dir_a, name))
        except (OSError, ValueError):
            size_a = None
        try:
            size_b = png_size(os.path.join(dir_b, name))
        except (OSError, ValueError):
            size_b = None
        rows.append((name, size_a, size_b, size_a is not None and size_a == size_b))
    return rows


# "Placement tolerance: major forms +/-5 mm" and friends. The gate must read
# its slack from the same spec the geometry came from, never from a constant
# buried in the checker.
TOLERANCE_RE = re.compile(r"(?i)[±+]/?-?\s*(\d+(?:\.\d+)?)\s*(mm|m)\b")
DEFAULT_TOLERANCE_M = 0.0


def spec_tolerance_m(build, default=DEFAULT_TOLERANCE_M):
    """Placement tolerance in metres, read out of the build's own units prose.

    The spec writes tolerance as English ("Placement tolerance: major forms
    +/-5 mm"), so this reads English. The largest stated tolerance wins: it is
    slack for the gate, and a gate that picks the tightest number would fail
    parts the spec explicitly allows to touch.
    """
    notes = []
    units = (build or {}).get("units") or {}
    notes.extend(units.get("tolerances") or [])
    notes.extend(units.get("notes") or [])
    best = None
    for note in notes:
        for value, unit in TOLERANCE_RE.findall(str(note)):
            metres = float(value) / 1000.0 if unit == "mm" else float(value)
            best = metres if best is None else max(best, metres)
    return default if best is None else best


def _pixel_box(box):
    """A flat [x0, y0, x1, y1] pixel box as a degenerate 3D AABB (z = 0)."""
    x0, y0, x1, y1 = (float(c) for c in box)
    return [[min(x0, x1), min(y0, y1), 0.0], [max(x0, x1), max(y0, y1), 1.0]]


def no_overlap(source=None, boxes=None, tolerance=None, names=None, allow=None):
    """Pairwise intersection test between named objects. Never raises on a
    legitimate empty result.

    Two modes, one return shape:

    * **Build mode** -- ``source`` is a build dict, or a path to a
      ``build.json``. Each object contributes the world AABB of every part of
      its compiled geometry (a jointed arm contributes one box per link, not
      one loose box around the whole arm), and a pair fails only when some
      part of one interpenetrates some part of the other by more than the
      tolerance on all three axes. Tolerance comes from the spec unless
      ``tolerance`` overrides it.
    * **Pixel mode** -- ``boxes`` is a list of flat ``[x0, y0, x1, y1]``
      boxes, for label sprites on a 2D frame. ``names`` labels them; indices
      are used when it does not.

    Returns::

        {"ok": bool,
         "pairs": [{"a": name, "b": name, "overlap": [dx, dy, dz]}, ...],
         "reason": str | None,      # why the answer is not a real check
         "tolerance_m": float,
         "method": "aabb-parts" | "aabb-pixels",
         "checked": int}            # pairs actually compared

    ``ok`` is True with an empty ``pairs`` list when nothing overlaps. When
    there is nothing to check at all, ``ok`` is False and ``reason`` says so:
    an empty input is not a pass.

    Note on method: this is a part-wise **axis-aligned** test, not a true
    convex-hull test. Exact bounds for each primitive (see
    ``spec/geometry.py``) make it tight enough that a diagonal arm link no
    longer reports a collision with thin air; two slim bodies crossing
    diagonally can still report a false positive, which is the honest trade
    and is why the failure names the pair and the depth rather than just
    failing.
    """
    if boxes is not None:
        items = []
        for i, box in enumerate(boxes):
            try:
                aabb = _pixel_box(box)
            except (TypeError, ValueError):
                return {"ok": False, "pairs": [], "tolerance_m": 0.0,
                        "method": "aabb-pixels", "checked": 0,
                        "reason": "box %d is not [x0, y0, x1, y1]: %r" % (i, box)}
            label = names[i] if names and i < len(names) else str(i)
            items.append((label, [aabb]))
        tol = float(tolerance or 0.0)
        method = "aabb-pixels"
    else:
        build = source
        if isinstance(build, str):
            try:
                with open(build, encoding="utf-8") as f:
                    build = json.load(f)
            except (OSError, ValueError) as e:
                return {"ok": False, "pairs": [], "tolerance_m": 0.0,
                        "method": "aabb-parts", "checked": 0,
                        "reason": "could not read a build JSON at %s (%s)"
                                  % (source, e)}
        if not isinstance(build, dict) or not build.get("objects"):
            return {"ok": False, "pairs": [], "tolerance_m": 0.0,
                    "method": "aabb-parts", "checked": 0,
                    "reason": "nothing to check: pass a build dict with objects, "
                              "or pixel boxes= for the 2D label case"}
        tol = spec_tolerance_m(build) if tolerance is None else float(tolerance)
        wanted = set(names) if names else None
        items = []
        for obj in build["objects"]:
            if wanted and obj.get("name") not in wanted:
                continue
            try:
                items.append((obj.get("name"), geometry_mod.object_world_boxes(obj)))
            except geometry_mod.GeometryError as e:
                return {"ok": False, "pairs": [], "tolerance_m": tol,
                        "method": "aabb-parts", "checked": 0,
                        "reason": "object %r has geometry this gate cannot bound "
                                  "(%s)" % (obj.get("name"), e)}
        method = "aabb-parts"

    if len(items) < 2:
        return {"ok": False, "pairs": [], "tolerance_m": tol, "method": method,
                "checked": 0,
                "reason": "need at least two objects to compare, got %d"
                          % len(items)}

    exempt = {tuple(sorted(pair)) for pair in (allow or [])}
    pairs = []
    checked = 0
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            name_a, boxes_a = items[i]
            name_b, boxes_b = items[j]
            checked += 1
            if tuple(sorted((name_a, name_b))) in exempt:
                continue
            worst = None
            for box_a in boxes_a:
                for box_b in boxes_b:
                    if geometry_mod.aabbs_overlap(box_a, box_b, tol):
                        depth = geometry_mod.overlap_depth(box_a, box_b)
                        if worst is None or min(depth) > min(worst):
                            worst = depth
            if worst is not None:
                pairs.append({"a": name_a, "b": name_b, "overlap": worst})
    pairs.sort(key=lambda p: (p["a"] or "", p["b"] or ""))
    return {"ok": not pairs, "pairs": pairs, "reason": None,
            "tolerance_m": tol, "method": method, "checked": checked}
