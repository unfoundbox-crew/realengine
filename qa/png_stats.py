"""Mean-pixel-value gate: proof a headless render is not a black frame.

qa/run_qa.py's OCR gate can be skipped (best-effort in CI, see ci.yml) --
this module is the hard, always-on gate: a rendered scene with everything
misconfigured (dead light, wrong camera, WebGL context that never painted)
tends to come back solid black. A PNG whose RGB channels average near zero
is that failure, cheap to catch without a browser, without PIL, without
numpy -- just zlib (stdlib) to inflate IDAT and a hand-rolled unfilter.

Supports bit depth 8 only, colour types 0 (grey), 2 (RGB), 4 (grey+alpha),
6 (RGBA) -- exactly what web/render_views.py's screenshots produce. Any
other bit depth or colour type raises ValueError; this fails closed rather
than silently mis-reading a frame as darker or lighter than it is.

CLI:
    python3 qa/png_stats.py <png> [<png>...] [--min-mean 8.0] [--json]

Exits 0 iff every file's mean RGB value is >= --min-mean, 2 on a read error.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# bytes per pixel, by PNG colour type, at bit depth 8.
_CHANNELS = {0: 1, 2: 3, 4: 2, 6: 4}


def _read_chunks(data):
    """Yield (ctype, cdata) for every chunk after the 8-byte signature."""
    pos = len(PNG_SIGNATURE)
    n = len(data)
    while pos + 8 <= n:
        length, ctype = struct.unpack(">I4s", data[pos:pos + 8])
        start = pos + 8
        end = start + length
        if end + 4 > n:
            raise ValueError("truncated chunk %r" % ctype)
        yield ctype, data[start:end]
        pos = end + 4  # skip the trailing CRC


def png_mean(path):
    """Mean of the RGB channels (0..255) over every pixel in the PNG.

    Alpha is ignored. Raises ValueError for anything outside bit depth 8,
    colour type 0/2/4/6 (interlaced or exotic PNGs are out of scope --
    fail loud rather than guess), and OSError if the file can't be read.
    """
    with open(path, "rb") as f:
        data = f.read()

    if data[:8] != PNG_SIGNATURE:
        raise ValueError("not a PNG: %s" % path)

    width = height = bit_depth = colour_type = interlace = None
    idat = bytearray()
    saw_ihdr = False

    for ctype, cdata in _read_chunks(data):
        if ctype == b"IHDR":
            if len(cdata) < 13:
                raise ValueError("short IHDR: %s" % path)
            (width, height, bit_depth, colour_type, _compression,
             _filter_method, interlace) = struct.unpack(">IIBBBBB", cdata[:13])
            saw_ihdr = True
        elif ctype == b"IDAT":
            idat += cdata
        elif ctype == b"IEND":
            break

    if not saw_ihdr:
        raise ValueError("missing IHDR: %s" % path)
    if bit_depth != 8:
        raise ValueError("unsupported bit depth %d (need 8): %s" % (bit_depth, path))
    if colour_type not in _CHANNELS:
        raise ValueError("unsupported colour type %d: %s" % (colour_type, path))
    if interlace:
        raise ValueError("interlaced PNGs are unsupported: %s" % path)
    if width <= 0 or height <= 0:
        raise ValueError("empty image %dx%d: %s" % (width, height, path))

    channels = _CHANNELS[colour_type]
    raw = zlib.decompress(bytes(idat))

    stride = width * channels
    expected_len = height * (stride + 1)  # +1 filter-type byte per scanline
    if len(raw) < expected_len:
        raise ValueError("decompressed data too short for %dx%d: %s" % (width, height, path))

    # Unfilter every scanline (PNG filters 0-4), keeping the previous
    # unfiltered row for the Up/Average/Paeth predictors.
    prev = bytearray(stride)
    total = 0
    count = 0
    rgb_channels = min(channels, 3)  # colour types 4 (grey+alpha) treat grey as R=G=B below
    pos = 0
    for _row in range(height):
        ftype = raw[pos]
        pos += 1
        cur = bytearray(raw[pos:pos + stride])
        pos += stride

        if ftype == 0:
            pass
        elif ftype == 1:  # Sub
            for i in range(channels, stride):
                cur[i] = (cur[i] + cur[i - channels]) & 0xFF
        elif ftype == 2:  # Up
            for i in range(stride):
                cur[i] = (cur[i] + prev[i]) & 0xFF
        elif ftype == 3:  # Average
            for i in range(stride):
                left = cur[i - channels] if i >= channels else 0
                cur[i] = (cur[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:  # Paeth
            for i in range(stride):
                left = cur[i - channels] if i >= channels else 0
                up = prev[i]
                up_left = prev[i - channels] if i >= channels else 0
                cur[i] = (cur[i] + _paeth(left, up, up_left)) & 0xFF
        else:
            raise ValueError("unknown PNG filter type %d: %s" % (ftype, path))

        if colour_type in (0, 4):
            # grayscale (optionally + alpha): one sample is R=G=B
            for i in range(0, stride, channels):
                g = cur[i]
                total += g * 3
                count += 3
        else:
            # RGB or RGBA: first 3 bytes of each pixel are R, G, B
            for i in range(0, stride, channels):
                total += cur[i] + cur[i + 1] + cur[i + 2]
                count += 3

        prev = cur

    if count == 0:
        raise ValueError("no pixels read: %s" % path)
    return total / count


def _paeth(left, up, up_left):
    p = left + up - up_left
    pa = abs(p - left)
    pb = abs(p - up)
    pc = abs(p - up_left)
    if pa <= pb and pa <= pc:
        return left
    if pb <= pc:
        return up
    return up_left


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pngs", nargs="+", help="PNG file(s) to check")
    ap.add_argument("--min-mean", type=float, default=8.0,
                     help="minimum acceptable mean RGB value, 0..255 (default: 8.0)")
    ap.add_argument("--json", action="store_true",
                     help="print a JSON receipt on stdout instead of plain lines")
    args = ap.parse_args(argv)

    results = []
    ok = True
    for path in args.pngs:
        try:
            mean = png_mean(path)
        except (OSError, ValueError, zlib.error) as exc:
            print("ERROR %s: %s" % (path, exc), file=sys.stderr)
            results.append({"file": path, "error": str(exc)})
            ok = False
            continue
        passed = mean >= args.min_mean
        ok = ok and passed
        results.append({"file": path, "mean": mean, "pass": passed})
        if not args.json:
            print("%s %s (mean=%.3f, min=%.3f)" %
                  ("PASS" if passed else "FAIL", path, mean, args.min_mean))

    if args.json:
        print(json.dumps({"ok": ok, "min_mean": args.min_mean, "files": results},
                          sort_keys=True))

    if any("error" in r for r in results):
        return 2
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
