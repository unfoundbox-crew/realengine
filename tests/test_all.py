#!/usr/bin/env python3
"""Standard library test suite for RealEngine (code-to-3d).

Tests:
- spec/validate.py
- web/build_web.py
- qa/asserts.py
- blender/build.py & ctd_blender
"""

import json
import math
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
import compile_brief
import build_web
import build_scene
from asserts import png_size, views_match, no_overlap, spec_tolerance_m
import geometry
from ctd_blender import primitives
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

    def test_no_overlap_needs_something_to_check(self):
        """An empty input is not a pass, and it is not an exception either."""
        result = no_overlap()
        self.assertFalse(result["ok"])
        self.assertIn("nothing to check", result["reason"])
        self.assertEqual(result["pairs"], [])


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


class TestBriefCompiler(unittest.TestCase):
    """The prompt->spec compiler: stubbed drafting, strict checks, offline compile."""

    def test_check_spec_accepts_the_golden_spec(self):
        text = (GOLDEN / "brain.emitted.md").read_text(encoding="utf-8")
        self.assertEqual(compile_brief.check_spec(text), [])

    def test_check_spec_rejects_an_incomplete_spec(self):
        problems = compile_brief.check_spec("# Nothing\n\n## Units\nmetric\n")
        self.assertTrue(problems)
        self.assertTrue(any("camera" in p or "validate.py" in p for p in problems))

    def test_strip_fence_unwraps_a_fenced_document(self):
        self.assertEqual(compile_brief.strip_fence("```markdown\n# Hi\n```"), "# Hi\n")
        self.assertEqual(compile_brief.strip_fence("# Hi"), "# Hi\n")

    def test_brief_id_is_deterministic_and_input_sensitive(self):
        a = compile_brief.brief_id_for("a robot arm", [])
        self.assertEqual(a, compile_brief.brief_id_for("a robot arm", []))
        self.assertNotEqual(a, compile_brief.brief_id_for("a robot arm", ["ref"]))

    def test_brief_fails_closed_without_a_configured_model(self):
        env = {k: v for k, v in os.environ.items()
               if k not in ("REALENGINE_LLM_BASE_URL", "LITELLM_BASE_URL",
                            "REALENGINE_LLM_API_KEY", "LITELLM_MASTER_KEY",
                            "REALENGINE_LLM_STUB")}
        with self.assertRaises(Exception) as cm:
            compile_brief.draft("a robot arm", env=env)
        self.assertIn("REALENGINE_LLM_BASE_URL", str(cm.exception))

    def test_brief_with_a_stub_produces_the_pinned_spec(self):
        pinned = json.loads((GOLDEN / "brain.hashes.json").read_text(encoding="utf-8"))
        env = dict(os.environ)
        env["REALENGINE_LLM_STUB"] = str(GOLDEN / "brain.emitted.md")
        text, meta, tried = compile_brief.draft("brain scene", env=env)
        self.assertEqual(meta["source"], "stub")
        self.assertEqual(len(tried), 1)
        self.assertEqual(scene_spec.compile_spec(text)["build_sha256"],
                         pinned["build_sha256"])


class TestWebSceneBackend(unittest.TestCase):
    """The Three.js backend: real page, no unbound slots, deterministic."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_build_scene_writes_a_complete_scene(self):
        receipt = build_scene.build_scene(str(BRAIN_SPEC), self.tmp)
        self.assertTrue(receipt["ok"])
        for key in ("html", "build_json", "views_json", "spec_md"):
            self.assertTrue(Path(receipt[key]).exists(), key)
        html = Path(receipt["html"]).read_text(encoding="utf-8")
        self.assertNotIn("{{", html)
        self.assertNotIn("}}", html)
        self.assertIn("CAM_Master", html)
        self.assertIn("Thalamus", html)
        self.assertIn(receipt["build_sha256"], html)

    def test_views_manifest_is_drivable_by_any_browser(self):
        receipt = build_scene.build_scene(str(BRAIN_SPEC), self.tmp)
        manifest = json.loads(Path(receipt["views_json"]).read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["views"]), len(receipt["cameras"]))
        for row in manifest["views"]:
            self.assertTrue(row["url"].startswith("scene.html?view=CAM_"))
            self.assertIn("hud=0", row["url"])
            self.assertGreater(row["res_x"], 0)
        self.assertIn("Thalamus", manifest["labels"])

    def test_build_is_byte_identical_on_a_second_run(self):
        a = build_scene.build_scene(str(BRAIN_SPEC), os.path.join(self.tmp, "a"))
        b = build_scene.build_scene(str(BRAIN_SPEC), os.path.join(self.tmp, "b"))
        self.assertEqual(Path(a["html"]).read_bytes(), Path(b["html"]).read_bytes())
        self.assertEqual(a["build_sha256"], b["build_sha256"])



LAMP_SPEC = REPO_ROOT / "examples/desk-lamp/SCENE_SPEC.md"


def _box(x0, y0, z0, x1, y1, z1):
    return [[x0, y0, z0], [x1, y1, z1]]


class TestGeometryCompiler(unittest.TestCase):
    """The geometry block: primitives, composition, and a labelled fallback."""

    def test_no_block_is_a_labelled_blockout_box(self):
        out = geometry.compile_object_geometry(None, [0.2, 0.3, 0.4])
        self.assertEqual(out["source"], "blockout")
        self.assertEqual(len(out["parts"]), 1)
        self.assertEqual(out["parts"][0]["kind"], "box")
        self.assertEqual(out["parts"][0]["size"], [0.2, 0.3, 0.4])
        self.assertEqual(out["aabb"], _box(-0.1, -0.15, -0.2, 0.1, 0.15, 0.2))
        self.assertEqual(out["warnings"], [])

    def test_sphere_bounds_are_exact(self):
        out = geometry.compile_object_geometry({"kind": "sphere", "radius": 0.03},
                                              [0.06, 0.06, 0.06])
        self.assertEqual(out["source"], "modelled")
        self.assertEqual(out["aabb"], _box(-0.03, -0.03, -0.03, 0.03, 0.03, 0.03))
        self.assertEqual(out["warnings"], [])

    def test_group_composes_child_offsets(self):
        block = {"kind": "group", "pos": [0, 0, 0.1], "parts": [
            {"kind": "cylinder", "radius": 0.05, "height": 0.02},
            {"kind": "torus", "radius": 0.04, "tube": 0.005, "pos": [0, 0, 0.03]},
        ]}
        out = geometry.compile_object_geometry(block, [0.1, 0.1, 0.05])
        self.assertEqual([p["kind"] for p in out["parts"]], ["cylinder", "torus"])
        self.assertEqual(out["parts"][0]["pos"], [0.0, 0.0, 0.1])
        self.assertEqual(out["parts"][1]["pos"], [0.0, 0.0, 0.13])

    def test_arm_becomes_aimed_links_plus_joint_balls(self):
        block = {"kind": "arm", "radius": 0.01, "joint_radius": 0.012,
                 "joints": [[0, 0, -0.1], [0.02, 0, 0.0], [0, 0, 0.1]]}
        out = geometry.compile_object_geometry(block, [0.1, 0.1, 0.2])
        kinds = [p["kind"] for p in out["parts"]]
        self.assertEqual(kinds, ["cylinder", "cylinder", "sphere", "sphere",
                                 "sphere"])
        # Each link is as long as its segment and sits at the segment midpoint.
        span = math.sqrt(0.02 ** 2 + 0.1 ** 2)
        self.assertAlmostEqual(out["parts"][0]["height"], round(span, 6), places=5)
        self.assertEqual(out["parts"][0]["pos"], [0.01, 0.0, -0.05])
        # A tilted link is genuinely tilted: not the identity quaternion.
        self.assertNotEqual(out["parts"][0]["quat"], [0.0, 0.0, 0.0, 1.0])

    def test_lathe_profile_drives_the_bounds(self):
        block = {"kind": "lathe", "segments": 12,
                 "profile": [[0.01, -0.05], [0.07, 0.05]]}
        out = geometry.compile_object_geometry(block, [0.14, 0.14, 0.1])
        self.assertEqual(out["aabb"], _box(-0.07, -0.07, -0.05, 0.07, 0.07, 0.05))
        self.assertEqual(out["warnings"], [])

    def test_a_declared_size_that_disagrees_warns_and_never_rescales(self):
        out = geometry.compile_object_geometry({"kind": "sphere", "radius": 0.05},
                                               [0.06, 0.06, 0.06])
        self.assertEqual(len(out["warnings"]), 3)
        self.assertIn("nothing was rescaled", out["warnings"][0])
        self.assertEqual(out["parts"][0]["radius"], 0.05)

    def test_rotated_cylinder_bounds_are_tighter_than_its_corner_box(self):
        part = geometry.compile_object_geometry(
            {"kind": "cylinder", "radius": 0.01, "height": 0.4,
             "rot_deg": [0, 90, 0]}, None)["parts"][0]
        lo, hi = geometry.part_aabb(part)
        self.assertAlmostEqual(hi[0] - lo[0], 0.4, places=5)
        self.assertAlmostEqual(hi[2] - lo[2], 0.02, places=5)

    def test_bad_blocks_fail_closed(self):
        for block in (
            {"kind": "blob"},
            {"kind": "group", "rot_deg": [0, 0, 45], "parts": [{"kind": "sphere", "radius": 1}]},
            {"kind": "group", "parts": []},
            {"kind": "arm", "joints": [[0, 0, 0], [0, 0, 0]]},
            {"kind": "cylinder", "radius": 0.01},          # no height
            {"kind": "lathe", "profile": [[0.01, 0.0]]},    # one point
        ):
            with self.assertRaises(geometry.GeometryError, msg=repr(block)):
                geometry.compile_object_geometry(block, [1, 1, 1])

    def test_compiler_is_deterministic(self):
        block = {"kind": "arm", "joints": [[0, 0, -0.1], [0.02, 0.01, 0.1]]}
        a = geometry.compile_object_geometry(block, [1, 1, 1])
        b = geometry.compile_object_geometry(block, [1, 1, 1])
        self.assertEqual(scene_spec.canonical_json(a), scene_spec.canonical_json(b))


class TestGeometryInTheSpec(unittest.TestCase):
    """The desk-lamp: the example that stops being boxes."""

    def setUp(self):
        self.text = LAMP_SPEC.read_text(encoding="utf-8")
        self.scene = scene_spec.parse_spec(self.text)
        self.build = scene_spec.to_build_json(self.scene)

    def test_golden_build_json(self):
        self.assertEqual(scene_spec.canonical_json(self.build),
                         (GOLDEN / "desk-lamp.build.json").read_text(encoding="utf-8"))

    def test_pinned_hashes(self):
        pinned = json.loads((GOLDEN / "desk-lamp.hashes.json").read_text(encoding="utf-8"))
        result = scene_spec.compile_spec(self.text)
        self.assertEqual(result["build_sha256"], pinned["build_sha256"])
        self.assertEqual(result["spec_sha256"], pinned["spec_sha256"])

    def test_non_box_objects_round_trip_unchanged(self):
        again = scene_spec.parse_spec(scene_spec.emit_spec(self.scene))
        self.assertEqual(scene_spec.canonical_json(again),
                         scene_spec.canonical_json(self.scene))
        self.assertEqual(again["geometry"], self.scene["geometry"])
        self.assertEqual(scene_spec.build_hash(scene_spec.to_build_json(again)),
                         scene_spec.build_hash(self.build))

    def test_emitted_spec_still_passes_the_validator(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as f:
            f.write(scene_spec.emit_spec(self.scene))
            path = f.name
        try:
            self.assertEqual(validate.main(path), 0)
        finally:
            os.remove(path)

    def test_every_object_names_its_source_and_the_bench_is_the_fallback(self):
        sources = {o["name"]: o["geometry"]["source"] for o in self.build["objects"]}
        self.assertEqual(sources["BNCH_Top"], "blockout")
        for name in ("LAMP_Base", "LAMP_LowerArm", "LAMP_UpperArm",
                     "LAMP_Shade", "GLOW_Bulb"):
            self.assertEqual(sources[name], "modelled", name)

    def test_the_shade_and_arms_are_not_boxes(self):
        kinds = {}
        for obj in self.build["objects"]:
            kinds[obj["name"]] = sorted({p["kind"] for p in obj["geometry"]["parts"]})
        self.assertEqual(kinds["LAMP_Shade"], ["lathe"])
        self.assertEqual(kinds["LAMP_Base"], ["cylinder", "torus"])
        self.assertEqual(kinds["LAMP_LowerArm"], ["cylinder", "sphere"])
        self.assertEqual(kinds["GLOW_Bulb"], ["sphere"])
        self.assertEqual(kinds["BNCH_Top"], ["box"])

    def test_no_geometry_block_means_no_geometry_key_at_all(self):
        """A spec written before geometry existed must build byte-identically."""
        brain = scene_spec.parse_spec(BRAIN_SPEC.read_text(encoding="utf-8"))
        self.assertNotIn("geometry", brain)
        for obj in scene_spec.to_build_json(brain)["objects"]:
            self.assertNotIn("geometry", obj)

    def test_the_modelled_geometry_matches_the_declared_dimensions(self):
        for obj in self.build["objects"]:
            self.assertEqual(obj["geometry"]["warnings"], [], obj["name"])


class TestNoOverlap(unittest.TestCase):
    """The overlap gate: real since this wave, and it never raises."""

    def _pair(self, a_pos, b_pos, size=(0.1, 0.1, 0.1), tolerance=None):
        objects = [{"name": "A", "pos": list(a_pos), "size_m": list(size)},
                   {"name": "B", "pos": list(b_pos), "size_m": list(size)}]
        build = {"objects": objects,
                 "units": {"tolerances": ["Placement tolerance: major forms ±5 mm"]}}
        return no_overlap(build, tolerance=tolerance)

    def test_a_known_colliding_pair_fails_and_names_it(self):
        result = self._pair((0, 0, 0), (0.05, 0, 0))
        self.assertFalse(result["ok"])
        self.assertEqual([(p["a"], p["b"]) for p in result["pairs"]], [("A", "B")])
        self.assertAlmostEqual(result["pairs"][0]["overlap"][0], 0.05, places=6)
        self.assertEqual(result["checked"], 1)
        self.assertIsNone(result["reason"])

    def test_a_disjoint_pair_passes_with_no_pairs(self):
        result = self._pair((0, 0, 0), (0.5, 0, 0))
        self.assertTrue(result["ok"])
        self.assertEqual(result["pairs"], [])
        self.assertIsNone(result["reason"])

    def test_tolerance_comes_from_the_spec_and_is_slack(self):
        # 4 mm of interpenetration, inside the spec's ±5 mm placement tolerance.
        result = self._pair((0, 0, 0), (0.096, 0, 0))
        self.assertEqual(result["tolerance_m"], 0.005)
        self.assertTrue(result["ok"])
        # The same pair with no slack at all is a collision.
        self.assertFalse(self._pair((0, 0, 0), (0.096, 0, 0), tolerance=0.0)["ok"])

    def test_spec_tolerance_reads_the_units_prose(self):
        self.assertEqual(spec_tolerance_m({"units": {"tolerances": ["±5 mm"]}}), 0.005)
        self.assertEqual(spec_tolerance_m({"units": {"notes": ["+/- 0.02 m"]}}), 0.02)
        self.assertEqual(spec_tolerance_m({}, default=0.001), 0.001)

    def test_touching_faces_are_not_a_collision(self):
        self.assertTrue(self._pair((0, 0, 0), (0.1, 0, 0), tolerance=0.0)["ok"])

    def test_parts_are_tested_pairwise_not_as_one_loose_box(self):
        """An L-shaped object's union box swallows its notch; its parts do not."""
        bracket = {"name": "BRACKET", "pos": [0, 0, 0], "geometry":
                   geometry.compile_object_geometry(
                       {"kind": "group", "parts": [
                           {"kind": "box", "size": [0.1, 0.1, 0.02],
                            "pos": [0, 0, -0.04]},
                           {"kind": "box", "size": [0.02, 0.1, 0.1],
                            "pos": [-0.04, 0, 0]}]}, None)}
        # Sits in the notch of the L: clear of both arms, inside the union box.
        pin = {"name": "PIN", "pos": [0.03, 0, 0.02], "size_m": [0.02, 0.02, 0.02]}
        union = geometry.union_aabb(bracket["geometry"]["parts"])
        self.assertTrue(geometry.aabbs_overlap(
            union, _box(0.02, -0.01, 0.01, 0.04, 0.01, 0.03)))
        result = no_overlap({"objects": [bracket, pin], "units": {}})
        self.assertTrue(result["ok"], result["pairs"])

    def test_the_desk_lamp_build_has_no_overlaps(self):
        build = scene_spec.compile_spec(LAMP_SPEC.read_text(encoding="utf-8"))["build"]
        result = no_overlap(build)
        self.assertTrue(result["ok"], result["pairs"])
        self.assertEqual(result["checked"], 15)
        self.assertEqual(result["tolerance_m"], 0.005)

    def test_pixel_mode_for_label_boxes(self):
        result = no_overlap(boxes=[[0, 0, 10, 10], [5, 5, 20, 20], [50, 50, 60, 60]],
                            names=["Thalamus", "Hippocampus", "Cortex"])
        self.assertFalse(result["ok"])
        self.assertEqual([(p["a"], p["b"]) for p in result["pairs"]],
                         [("Thalamus", "Hippocampus")])
        self.assertEqual(result["method"], "aabb-pixels")

    def test_an_allowed_pair_is_exempt(self):
        objects = [{"name": "A", "pos": [0, 0, 0], "size_m": [0.1, 0.1, 0.1]},
                   {"name": "B", "pos": [0.05, 0, 0], "size_m": [0.1, 0.1, 0.1]}]
        result = no_overlap({"objects": objects, "units": {}}, allow=[("B", "A")])
        self.assertTrue(result["ok"])

    def test_a_bad_input_reports_a_reason_instead_of_raising(self):
        self.assertIn("not [x0", no_overlap(boxes=[[1, 2, 3]])["reason"])
        self.assertIn("could not read", no_overlap("/nonexistent/build.json")["reason"])
        self.assertIn("at least two", no_overlap(
            {"objects": [{"name": "A", "pos": [0, 0, 0], "size_m": [1, 1, 1]}],
             "units": {}})["reason"])


class TestPrimitiveTessellation(unittest.TestCase):
    """Blender's half of the vocabulary, testable with no Blender installed."""

    PARTS = [
        {"kind": "box", "size": [1, 2, 3]},
        {"kind": "cylinder", "radius_bottom": 0.05, "radius_top": 0.05,
         "height": 0.2, "segments": 12},
        {"kind": "cone", "radius_bottom": 0.05, "radius_top": 0.0,
         "height": 0.2, "segments": 12},
        {"kind": "sphere", "radius": 0.05, "segments": 12, "rings": 6},
        {"kind": "torus", "radius": 0.05, "tube": 0.01, "segments": 12,
         "tube_segments": 8},
        {"kind": "lathe", "profile": [[0.01, 0.0], [0.05, 0.1], [0.05, 0.12]],
         "segments": 12},
        {"kind": "extrude", "outline": [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1]],
         "depth": 0.05},
    ]

    def test_every_kind_tessellates_to_a_sane_mesh(self):
        for part in self.PARTS:
            verts, faces = primitives.part_mesh(part)
            self.assertGreaterEqual(len(verts), 4, part["kind"])
            self.assertGreaterEqual(len(faces), 4, part["kind"])
            for face in faces:
                self.assertGreaterEqual(len(face), 3, part["kind"])
                self.assertEqual(len(set(face)), len(face), part["kind"])
                for index in face:
                    self.assertTrue(0 <= index < len(verts), part["kind"])

    def test_counts_are_what_the_maths_says(self):
        verts, faces = primitives.part_mesh(self.PARTS[1])   # cylinder, 12 seg
        self.assertEqual(len(verts), 24)
        self.assertEqual(len(faces), 14)                     # 12 walls + 2 caps
        verts, faces = primitives.part_mesh(self.PARTS[2])   # cone, 12 seg
        self.assertEqual(len(verts), 13)                     # ring + apex
        self.assertEqual(len(faces), 13)                     # 12 walls + 1 cap
        verts, _ = primitives.part_mesh(self.PARTS[4])       # torus 12x8
        self.assertEqual(len(verts), 96)

    def test_vertices_stay_inside_the_compiler_s_bounds(self):
        for part in self.PARTS:
            compiled = dict(part, pos=[0, 0, 0], quat=[0, 0, 0, 1])
            lo, hi = geometry.part_aabb(compiled)
            for vert in primitives.part_mesh(compiled)[0]:
                for i in range(3):
                    self.assertLessEqual(lo[i] - 1e-6, vert[i], part["kind"])
                    self.assertLessEqual(vert[i], hi[i] + 1e-6, part["kind"])

    def test_an_unknown_kind_fails_closed(self):
        with self.assertRaises(ValueError):
            primitives.part_mesh({"kind": "teapot"})


if __name__ == "__main__":
    unittest.main()
