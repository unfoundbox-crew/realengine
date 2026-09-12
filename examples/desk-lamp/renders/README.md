# Committed render evidence

One frame, kept in the tree because a claim about the light rig needs a
picture behind it.

| file | what it proves |
| --- | --- |
| `blender_CAM_LeftOrthographic.png` | The three-point rig in `blender/ctd_blender/lighting.py` lights a scene. The frame is lit (mean pixel 195.8, `qa/png_stats.py`), not the black frame every pre-rig Blender render produced. It also shows the modelled geometry: a turned base, a jointed arm with a visible elbow, a lathed shade. |

How it was made, on macOS with Blender 5.2.1 LTS:

```bash
python3 web/build_scene.py examples/desk-lamp/SCENE_SPEC.md --out-dir out/lamp
python3 blender/run_headless.py --spec out/lamp/build.json --out-dir out/lampblend \
    --views CAM_LeftOrthographic --samples 16 --res-scale 0.25
python3 qa/png_stats.py out/lampblend/CAM_LeftOrthographic.png --min-mean 8
```

400x400, 16 samples, Eevee, ~6 s. Blender is an optional dependency: with no
Blender installed `run_headless.py` exits 3 and names what is missing. CI does
not run Blender — the `views` job renders the same scene in headless Chromium
instead.
