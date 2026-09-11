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


if __name__ == "__main__":
    unittest.main()
