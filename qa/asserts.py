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
- no_overlap: STUB. Raises NotImplementedError; docstring sketches the
  future algorithm.

Stdlib only.
"""

import os
import shutil
import struct
import subprocess

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


def no_overlap(*args, **kwargs):
    """STUB -- label-overlap detection, not yet implemented.

    Future algorithm: render each label sprite in isolation (or threshold
    the label pass by its solid fill colour), run connected-component
    labelling over the binary mask to get one bounding box per label,
    then pairwise box-intersection test with a small pixel margin for
    anti-aliased edges. Any intersecting pair fails, reporting both
    label names and the overlap area in px. Until then, overlap is a
    human-eye check -- see the QA report.
    """
    raise NotImplementedError("no_overlap is a stub: overlap stays human-only until Wave 2")
