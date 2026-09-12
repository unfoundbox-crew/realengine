#!/usr/bin/env python3
"""Standard library test suite for RealEngine (code-to-3d).

Tests:
- spec/validate.py
- web/build_web.py
- qa/asserts.py
- blender/build.py & ctd_blender
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "spec"))
sys.path.insert(0, str(REPO_ROOT / "web"))
sys.path.insert(0, str(REPO_ROOT / "qa"))
sys.path.insert(0, str(REPO_ROOT / "blender"))

import validate
import scene_spec
import build_web
from asserts import png_size, views_match, no_overlap
import build
from ctd_blender.materials import hex_to_linear


class TestSpecValidate(unittest.TestCase):
    def test_valid_brain_spec(self):
        spec_path = REPO_ROOT / "examples/brain/SCENE_SPEC.md"
        self.assertTrue(spec_path.exists())
        ret = validate.main(str(spec_path))
        self.assertEqual(ret, 0)

    def test_missing_file(self):
        ret = validate.main(str(REPO_ROOT / "nonexistent_spec.md"))
        self.assertEqual(ret, 1)

    def test_missing_required_section(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as f:
            f.write("# Incomplete Spec\n## Units\nCAM_Master\n")
            f_path = f.name
        try:
            ret = validate.main(f_path)
            self.assertEqual(ret, 1)
        finally:
            os.remove(f_path)

    def test_bad_hex_color(self):
        valid_spec = (REPO_ROOT / "examples/brain/SCENE_SPEC.md").read_text()
        corrupted = valid_spec + "\npalette: - Corrupt #GG12ZZ\n"
        with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as f:
            f.write(corrupted)
            f_path = f.name
        try:
            ret = validate.main(f_path)
            self.assertEqual(ret, 1)
        finally:
            os.remove(f_path)


class TestBuildWeb(unittest.TestCase):
    def test_brain_build_matches_example(self):
        preset_path = REPO_ROOT / "web/presets/brain.json"
        template_path = REPO_ROOT / "web/template.html"
        example_path = REPO_ROOT / "web/examples/brain-v2.html"

        with tempfile.NamedTemporaryFile("w+", suffix=".html", delete=False) as f:
            out_path = f.name
        try:
            build_web.main(["build_web.py", str(preset_path), str(template_path), out_path])
            with open(out_path, "r", encoding="utf-8") as f_out, open(example_path, "r", encoding="utf-8") as f_exp:
                self.assertEqual(f_out.read(), f_exp.read())
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    def test_missing_slot_fails(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as f_preset:
            json.dump({"foo": "bar"}, f_preset)
            p_name = f_preset.name

        with tempfile.NamedTemporaryFile("w+", suffix=".html", delete=False) as f_tpl:
            f_tpl.write("<html>{{missing_slot}}</html>")
            t_name = f_tpl.name

        try:
            with self.assertRaises(SystemExit) as cm:
                build_web.main(["build_web.py", p_name, t_name, "out.html"])
            self.assertEqual(cm.exception.code, 1)
        finally:
            os.remove(p_name)
            os.remove(t_name)


class TestQaAsserts(unittest.TestCase):
    def test_png_size_valid(self):
        png_path = REPO_ROOT / "examples/brain/01_master_front.png"
        self.assertTrue(png_path.exists())
        w, h = png_size(str(png_path))
        self.assertEqual((w, h), (1536, 1536))

    def test_png_size_invalid(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".png", delete=False) as f:
            f.write("not a png file")
            f_path = f.name
        try:
            with self.assertRaises(ValueError):
                png_size(f_path)
        finally:
            os.remove(f_path)

    def test_views_match(self):
        render_dir = REPO_ROOT / "examples/brain"
        rows = views_match(str(render_dir), str(render_dir))
        self.assertTrue(len(rows) > 0)
        for name, sz_a, sz_b, match in rows:
            self.assertTrue(match)
            self.assertEqual(sz_a, sz_b)

    def test_no_overlap_stub(self):
        with self.assertRaises(NotImplementedError):
            no_overlap()


class TestBlenderBuild(unittest.TestCase):
    def test_hex_to_linear(self):
        r, g, b = hex_to_linear("#ffffff")
        self.assertAlmostEqual(r, 1.0)
        self.assertAlmostEqual(g, 1.0)
        self.assertAlmostEqual(b, 1.0)

        r0, g0, b0 = hex_to_linear("#000000")
        self.assertAlmostEqual(r0, 0.0)
        self.assertAlmostEqual(g0, 0.0)
        self.assertAlmostEqual(b0, 0.0)

    def test_load_spec(self):
        self.assertEqual(build.load_spec(None), {})
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as f:
            json.dump({"scene": "TEST"}, f)
            p = f.name
        try:
            spec = build.load_spec(p)
            self.assertEqual(spec.get("scene"), "TEST")
        finally:
            os.remove(p)


GOLDEN = REPO_ROOT / "tests/golden"
BRAIN_SPEC = REPO_ROOT / "examples/brain/SCENE_SPEC.md"


class TestSceneSpecRoundTrip(unittest.TestCase):
    """SCENE_SPEC.md <-> JSON: golden files + fixpoint + pinned hashes."""

    def setUp(self):
        self.text = BRAIN_SPEC.read_text(encoding="utf-8")
        self.scene = scene_spec.parse_spec(self.text)

    def test_golden_scene_json(self):
        self.assertEqual(scene_spec.canonical_json(self.scene),
                         (GOLDEN / "brain.scene.json").read_text(encoding="utf-8"))

    def test_golden_build_json(self):
        build = scene_spec.to_build_json(self.scene)
        self.assertEqual(scene_spec.canonical_json(build),
                         (GOLDEN / "brain.build.json").read_text(encoding="utf-8"))

    def test_golden_emitted_markdown(self):
        self.assertEqual(scene_spec.emit_spec(self.scene),
                         (GOLDEN / "brain.emitted.md").read_text(encoding="utf-8"))

    def test_pinned_hashes(self):
        pinned = json.loads((GOLDEN / "brain.hashes.json").read_text(encoding="utf-8"))
        result = scene_spec.compile_spec(self.text)
        self.assertEqual(result["build_sha256"], pinned["build_sha256"])
        self.assertEqual(result["spec_sha256"], pinned["spec_sha256"])

    def test_emit_parse_is_a_fixpoint(self):
        again = scene_spec.parse_spec(scene_spec.emit_spec(self.scene))
        self.assertEqual(scene_spec.canonical_json(again),
                         scene_spec.canonical_json(self.scene))
        third = scene_spec.parse_spec(scene_spec.emit_spec(again))
        self.assertEqual(scene_spec.canonical_json(third),
                         scene_spec.canonical_json(again))

    def test_emitted_spec_passes_validator(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as f:
            f.write(scene_spec.emit_spec(self.scene))
            path = f.name
        try:
            self.assertEqual(validate.main(path), 0)
        finally:
            os.remove(path)

    def test_parsed_content(self):
        self.assertEqual(self.scene["scene"], "Human_Brain_Predictive_Control")
        self.assertEqual(len(self.scene["cameras"]), 6)
        self.assertEqual(len(self.scene["build_order"]), 20)
        self.assertEqual(self.scene["palette"]["Frontal"]["hex"], "#7EA6FF")
        # #E8EEF3 must not truncate to the 3-digit form #E8E
        self.assertEqual(self.scene["palette"]["Head"]["hex"], "#E8EEF3")
        names = [o["name"] for o in self.scene["objects"]]
        self.assertIn("SUB_Thalamus", names)
        self.assertIn("CTX_Occipital", names)
        thal = [o for o in self.scene["objects"] if o["name"] == "SUB_Thalamus"][0]
        self.assertEqual(thal["size_mm"], [35.0, 28.0, 25.0])
        self.assertEqual(thal["collection"], "03_SUBCORTICAL")
        self.assertTrue(self.scene["priority"].startswith("scene_spec.md >"))

    def test_build_json_is_blender_build_compatible(self):
        bj = scene_spec.to_build_json(self.scene)
        # exactly the keys blender/build.py reads
        for key in ("scene", "collections", "palette", "cameras", "views"):
            self.assertIn(key, bj)
        for cam in bj["cameras"]:
            self.assertEqual(len(cam["pos"]), 3)
            self.assertEqual(len(cam["target"]), 3)
        for view in bj["views"]:
            self.assertTrue(view["output"].endswith(".png"))
        # blender/build.py's own loader must accept it unchanged
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as f:
            f.write(scene_spec.canonical_json(bj))
            path = f.name
        try:
            loaded = build.load_spec(path)
            self.assertEqual(loaded["scene"], bj["scene"])
            self.assertEqual(loaded["collections"], bj["collections"])
        finally:
            os.remove(path)

    def test_hash_is_stable_across_parses(self):
        a = scene_spec.compile_spec(self.text)["build_sha256"]
        b = scene_spec.compile_spec(self.text)["build_sha256"]
        self.assertEqual(a, b)

    def test_hash_changes_when_spec_changes(self):
        mutated = self.text.replace("#7EA6FF", "#7EA6FE")
        self.assertNotEqual(scene_spec.compile_spec(mutated)["build_sha256"],
                            scene_spec.compile_spec(self.text)["build_sha256"])


if __name__ == "__main__":
    unittest.main()
