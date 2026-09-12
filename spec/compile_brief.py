#!/usr/bin/env python3
"""The prompt -> spec compiler: brief in, pinned SCENE_SPEC.md out.

Two commands, and the split between them is the whole point:

    brief    words -> a drafted SCENE_SPEC.md. The ONLY step that calls a
             model. The draft is rejected unless it passes spec/validate.py
             AND parses into a complete scene (>=1 camera, >=1 object, >=1
             palette entry, gapless build order, a priority rule). One retry
             with the failures fed back, then it fails closed.

    compile  a stored (or given) SCENE_SPEC.md -> validated build JSON plus
             both hashes. Pure code: deterministic, offline, no model.

So a scene is reproducible from the spec file alone. The model gets one job,
early, and its output is a human-readable artifact a person can edit.

Usage:
    python3 spec/compile_brief.py brief   --prompt "..." [--refs a,b]
                                          [--store DIR] [--model M]
    python3 spec/compile_brief.py compile (--brief-id ID | --spec PATH)
                                          [--store DIR] [--out-dir DIR]

Prints a one-line JSON receipt on stdout; logs go to stderr. Stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import llm  # noqa: E402
import scene_spec  # noqa: E402
import validate  # noqa: E402

DEFAULT_STORE = ".realengine"

SYSTEM_PROMPT = """\
You write SCENE_SPEC.md files for RealEngine: a deterministic 3D build \
contract that both a human and a parser read. Output ONLY the Markdown file \
-- no preamble, no code fence around the whole document, no commentary.

The file MUST contain these H2 sections, spelled as given:

## Units and coordinates
  Bullets. State metric units, which axis is up, and one envelope bullet per
  major volume, e.g. "- Scene envelope: `0.400 × 0.300 × 0.250 m`".

## Palette
  One bullet per named colour, name then a hex in backticks, optionally
  alpha and roughness:  "- Chassis `#7EA6FF` alpha 1 roughness 0.45"
  Hex must be #RGB, #RRGGBB or #RRGGBBAA. Nothing else in this file may
  contain a "#" followed by non-hex characters.

## Collections
  A ```text fenced block: "SCENE" then one line per collection, numbered
  and prefixed, e.g. "├── 02_BODY".

## Naming
  A ```text fenced block mapping each object prefix to its collection:
  "BODY_ -> 02_BODY". Then a second ```text block listing every object as
  PREFIX_Name, one per line. Prefixes are 2+ capitals.

## Object dimensions
  One bullet per object: "- BODY_Frame: `120 × 40 × 30 mm`".

## Cameras
  One bullet per camera, at least one, named `CAM_Something`, with a short
  description after an em dash. Include an orthographic view or two by
  putting "Orthographic" in the name (e.g. `CAM_LeftOrthographic`).

## Functional labels
  One bullet per label: "Name — short subtitle". The Name must match an
  object's suffix so labels bind to volumes.

## Render
  Bullets: "- master `1600×900`", "- orthographic refs `1200×1200`", engine.

## Lighting
  A line containing a background hex in backticks.

## Deterministic build order
  A ```text fenced block, steps numbered from 01 with no gaps: "01 collections".

## Priority
  A line: "Conflict priority: `scene_spec.md > orthographic views > master \
perspective > detail aesthetics`".

Rules: every colour is a well-formed hex; build steps start at 01 and are \
gapless; object names carry their prefix; label text is exact display text. \
Do not invent facts about a real subject you were not given -- keep shapes, \
counts and names to what the brief states or plainly implies.
"""


def log(msg):
    print("compile_brief: %s" % msg, file=sys.stderr)


def brief_id_for(prompt, refs):
    canonical = json.dumps({"prompt": prompt.strip(), "refs": list(refs)},
                           sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def store_dir(store=None):
    return Path(store or os.environ.get("REALENGINE_STORE") or DEFAULT_STORE).resolve()


def strip_fence(text):
    """Models like to wrap the whole file in ```markdown. Unwrap it."""
    t = text.strip()
    if t.startswith("```"):
        first = t.index("\n") + 1 if "\n" in t else len(t)
        head = t[:first].strip().lower()
        if head in ("```", "```markdown", "```md"):
            end = t.rfind("```")
            if end > first:
                return t[first:end].strip() + "\n"
    return t + "\n" if not t.endswith("\n") else t


def check_spec(text):
    """Strict schema check. Returns a list of problems; empty means good."""
    problems = []
    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False,
                                     encoding="utf-8") as f:
        f.write(text)
        path = f.name
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = validate.main(path)
        if code != 0:
            for line in buf.getvalue().splitlines():
                line = line.strip()
                if line.startswith("- "):
                    problems.append("validate.py: " + line[2:])
            if not problems:
                problems.append("validate.py rejected the spec")
    finally:
        os.remove(path)

    try:
        scene = scene_spec.parse_spec(text)
    except Exception as exc:  # a parser crash is a spec problem, not a bug
        return problems + ["parser could not read the spec: %s" % exc]

    if not scene["cameras"]:
        problems.append("no CAM_* camera found in the Cameras section")
    if not scene["objects"]:
        problems.append("no PREFIX_Name objects found in the Naming section")
    if not scene["palette"]:
        problems.append("no named hex colours found in the Palette section")
    if not scene["collections"]:
        problems.append("no collection tree found in the Collections section")
    if len(scene["build_order"]) < 2:
        problems.append("build order needs at least 2 numbered steps")
    if not scene["priority"]:
        problems.append("no 'Conflict priority:' line found")
    if not scene["labels"]:
        problems.append("no labels found in the Functional labels section")
    return problems


def draft(prompt, refs=(), env=None, attempts=2):
    """Draft a SCENE_SPEC.md that passes the schema check, or fail closed."""
    env = os.environ if env is None else env
    user = "Brief:\n%s\n" % prompt.strip()
    if refs:
        user += "\nReference material the author supplied:\n" + \
                "\n".join("- %s" % r for r in refs) + "\n"
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user}]

    tried = []
    for attempt in range(1, attempts + 1):
        text, meta = llm.chat(messages, env=env)
        spec_text = strip_fence(text)
        problems = check_spec(spec_text)
        tried.append({"attempt": attempt, "problems": problems,
                      "source": meta.get("source"), "model": meta.get("model")})
        if not problems:
            return spec_text, meta, tried
        log("attempt %d rejected: %s" % (attempt, "; ".join(problems[:4])))
        if attempt == attempts:
            break
        messages = messages + [
            {"role": "assistant", "content": spec_text},
            {"role": "user", "content":
             "That draft failed the schema check:\n"
             + "\n".join("- %s" % p for p in problems)
             + "\nReturn the corrected full SCENE_SPEC.md, nothing else."},
        ]
    raise llm.LLMUnavailable(
        "drafted spec failed the schema check %d time(s): %s"
        % (attempts, "; ".join(tried[-1]["problems"])))


def cmd_brief(args):
    refs = [r.strip() for r in (args.refs or "").split(",") if r.strip()]
    bid = brief_id_for(args.prompt, refs)
    root = store_dir(args.store) / "briefs" / bid
    root.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    if args.model:
        env["REALENGINE_LLM_MODEL"] = args.model

    brief_record = {"brief_id": bid, "prompt": args.prompt.strip(),
                    "refs": refs, "store": str(root)}
    (root / "brief.json").write_text(
        scene_spec.canonical_json(brief_record), encoding="utf-8")

    try:
        spec_text, meta, tried = draft(args.prompt, refs, env=env)
    except llm.LLMUnavailable as exc:
        return {"ok": False, "brief_id": bid, "brief_json": str(root / "brief.json"),
                "error": str(exc),
                "hint": ("The brief is recorded. Write %s by hand (see "
                         "spec/SPEC-SCHEMA.md) and run `compile --brief-id %s`."
                         % (root / "SCENE_SPEC.md", bid))}

    spec_path = root / "SCENE_SPEC.md"
    spec_path.write_text(spec_text, encoding="utf-8")
    compiled = scene_spec.compile_spec(spec_text)
    (root / "build.json").write_text(
        scene_spec.canonical_json(compiled["build"]), encoding="utf-8")

    return {
        "ok": True,
        "brief_id": bid,
        "brief_json": str(root / "brief.json"),
        "spec_path": str(spec_path),
        "build_json": str(root / "build.json"),
        "spec_sha256": compiled["spec_sha256"],
        "build_sha256": compiled["build_sha256"],
        "source": meta.get("source"),
        "model": meta.get("model"),
        "attempts": len(tried),
        "objects": len(compiled["scene"]["objects"]),
        "cameras": [c["name"] for c in compiled["scene"]["cameras"]],
        "note": ("Human Gate 1: read %s before building. Everything after "
                 "this point is deterministic and offline." % spec_path),
    }


def cmd_compile(args):
    if args.spec:
        spec_path = Path(args.spec).resolve()
    else:
        spec_path = store_dir(args.store) / "briefs" / args.brief_id / "SCENE_SPEC.md"
    if not spec_path.exists():
        return {"ok": False, "error": "no spec at %s" % spec_path}

    text = spec_path.read_text(encoding="utf-8")
    problems = check_spec(text)
    if problems:
        return {"ok": False, "spec_path": str(spec_path), "problems": problems,
                "error": "spec failed the schema check (%d problem(s))" % len(problems)}

    compiled = scene_spec.compile_spec(text)
    out_dir = Path(args.out_dir).resolve() if args.out_dir else spec_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    build_path = out_dir / "build.json"
    build_path.write_text(scene_spec.canonical_json(compiled["build"]),
                          encoding="utf-8")
    return {
        "ok": True,
        "spec_path": str(spec_path),
        "build_json": str(build_path),
        "spec_sha256": compiled["spec_sha256"],
        "build_sha256": compiled["build_sha256"],
        "scene": compiled["build"]["scene"],
        "objects": len(compiled["build"]["objects"]),
        "collections": compiled["build"]["collections"],
        "cameras": [c["name"] for c in compiled["build"]["cameras"]],
        "labels": [l["name"] for l in compiled["build"]["labels"]],
        "deterministic": True,
        "offline": True,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)

    b = sub.add_parser("brief", help="words -> drafted SCENE_SPEC.md (uses a model)")
    b.add_argument("--prompt", required=True)
    b.add_argument("--refs", default="")
    b.add_argument("--store", default=None)
    b.add_argument("--model", default=None)

    c = sub.add_parser("compile", help="SCENE_SPEC.md -> build JSON + hashes (offline)")
    g = c.add_mutually_exclusive_group(required=True)
    g.add_argument("--brief-id")
    g.add_argument("--spec")
    c.add_argument("--store", default=None)
    c.add_argument("--out-dir", default=None)

    args = ap.parse_args(argv)
    receipt = cmd_brief(args) if args.command == "brief" else cmd_compile(args)
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
