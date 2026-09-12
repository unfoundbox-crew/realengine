// code-to-3d MCP handlers — real work, no stubs.
//
// Every handler validates its args, then shells out to the Python step that
// owns the job and returns that step's JSON receipt verbatim. The scripts
// are the single implementation; this file is the MCP surface over them.
//
//   brief         spec/compile_brief.py brief     (the only networked step)
//   spec_compile  spec/compile_brief.py compile   (offline, deterministic)
//   build         web/build_scene.py | blender/run_headless.py
//   views         web/render_views.py             (headless Chromium, optional)
//   qa_assert     qa/run_qa.py --json             (zero-vision OCR)
//   export_scene  tools/export_scene.py
//
// A step that cannot run says which dependency is missing and returns
// ok:false. Nothing here pretends: no silent fallback, no invented paths.
//
// Environment:
//   REALENGINE_ROOT    repo root (default: two levels up from dist/)
//   REALENGINE_PYTHON  python interpreter (default: python3)

import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

export type ToolResult = { ok: boolean; [key: string]: unknown };
export type HandlerArgs = Record<string, unknown>;

const HERE = path.dirname(fileURLToPath(import.meta.url));

export function repoRoot(): string {
  return process.env.REALENGINE_ROOT ?? path.resolve(HERE, "..", "..");
}

function python(): string {
  return process.env.REALENGINE_PYTHON ?? "python3";
}

const fail = (error: string, extra: Record<string, unknown> = {}): ToolResult => ({
  ok: false,
  error,
  ...extra,
});

function nonEmptyString(v: unknown): v is string {
  return typeof v === "string" && v.trim().length > 0;
}

function stringArray(v: unknown): v is string[] {
  return Array.isArray(v) && v.every((x) => typeof x === "string");
}

/** Last non-empty stdout line, which is where every script prints its receipt. */
function lastJsonLine(stdout: string): unknown {
  const lines = stdout.split("\n").map((l) => l.trim()).filter(Boolean);
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    if (lines[i].startsWith("{")) {
      try {
        return JSON.parse(lines[i]);
      } catch {
        /* keep looking backwards */
      }
    }
  }
  return null;
}

export function runPython(script: string, args: string[]): ToolResult {
  const root = repoRoot();
  const scriptPath = path.join(root, script);
  const res = spawnSync(python(), [scriptPath, ...args], {
    cwd: root,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
    env: process.env,
  });
  if (res.error) {
    return fail(`could not run ${python()} ${script}: ${String(res.error)}`, {
      script,
      hint: "set REALENGINE_PYTHON to a python3 interpreter",
    });
  }
  const parsed = lastJsonLine(res.stdout ?? "");
  if (parsed && typeof parsed === "object") {
    const receipt = parsed as ToolResult;
    if (typeof receipt.ok !== "boolean") receipt.ok = res.status === 0;
    return receipt;
  }
  return fail(`${script} produced no JSON receipt (exit ${res.status})`, {
    script,
    exit_code: res.status,
    stderr_tail: (res.stderr ?? "").trim().slice(-1200),
  });
}

/** brief: words -> a drafted, schema-checked SCENE_SPEC.md. Calls a model. */
export function handleBrief(args: HandlerArgs): ToolResult {
  if (!nonEmptyString(args.prompt)) {
    return fail("brief rejected: 'prompt' must be a non-empty string.");
  }
  if (args.refs !== undefined && !stringArray(args.refs)) {
    return fail("brief rejected: 'refs' must be an array of strings when provided.");
  }
  const argv = ["brief", "--prompt", args.prompt];
  if (stringArray(args.refs) && args.refs.length) argv.push("--refs", args.refs.join(","));
  if (nonEmptyString(args.store)) argv.push("--store", args.store);
  if (nonEmptyString(args.model)) argv.push("--model", args.model);
  return runPython("spec/compile_brief.py", argv);
}

/** spec_compile: a stored or given spec -> validated build JSON + hashes. */
export function handleSpecCompile(args: HandlerArgs): ToolResult {
  const hasId = nonEmptyString(args.brief_id);
  const hasPath = nonEmptyString(args.spec_path);
  if (!hasId && !hasPath) {
    return fail("spec_compile rejected: pass 'brief_id' or 'spec_path'.");
  }
  if (hasId && hasPath) {
    return fail("spec_compile rejected: pass 'brief_id' or 'spec_path', not both.");
  }
  const argv = ["compile"];
  if (hasId) argv.push("--brief-id", args.brief_id as string);
  else argv.push("--spec", args.spec_path as string);
  if (nonEmptyString(args.store)) argv.push("--store", args.store);
  if (nonEmptyString(args.out_dir)) argv.push("--out-dir", args.out_dir);
  return runPython("spec/compile_brief.py", argv);
}

/** build: an approved spec -> a scene on the web or blender backend. */
export function handleBuild(args: HandlerArgs): ToolResult {
  if (!nonEmptyString(args.spec_path)) {
    return fail("build rejected: 'spec_path' must be a non-empty string.");
  }
  if (args.backend !== "blender" && args.backend !== "web") {
    return fail("build rejected: 'backend' must be 'blender' or 'web'.");
  }
  if (args.out_dir !== undefined && !nonEmptyString(args.out_dir)) {
    return fail("build rejected: 'out_dir' must be a non-empty string when provided.");
  }
  const outDir = nonEmptyString(args.out_dir) ? args.out_dir : "out/scene";

  if (args.backend === "web") {
    return runPython("web/build_scene.py", [args.spec_path, "--out-dir", outDir]);
  }

  // Blender: compile the spec to build JSON first, then drive headless Blender.
  const compiled = runPython("spec/compile_brief.py", [
    "compile",
    "--spec",
    args.spec_path,
    "--out-dir",
    outDir,
  ]);
  if (!compiled.ok) return compiled;
  const argv = [
    "--spec",
    String(compiled.build_json),
    "--out-dir",
    path.join(outDir, "blender"),
  ];
  if (nonEmptyString(args.engine)) argv.push("--engine", args.engine);
  if (typeof args.samples === "number") argv.push("--samples", String(args.samples));
  if (typeof args.res_scale === "number") argv.push("--res-scale", String(args.res_scale));
  const built = runPython("blender/run_headless.py", argv);
  return {
    ...built,
    build_json: compiled.build_json,
    spec_sha256: compiled.spec_sha256,
    build_sha256: compiled.build_sha256,
  };
}

/** views: render the named camera views of a built scene to PNGs. */
export function handleViews(args: HandlerArgs): ToolResult {
  if (!nonEmptyString(args.scene)) {
    return fail("views rejected: 'scene' must be a non-empty string (the scene directory).");
  }
  if (args.cameras !== undefined && !stringArray(args.cameras)) {
    return fail("views rejected: 'cameras' must be an array of strings when provided.");
  }
  const argv = ["--scene-dir", args.scene];
  if (stringArray(args.cameras) && args.cameras.length) {
    argv.push("--views", args.cameras.join(","));
  }
  if (nonEmptyString(args.out_dir)) argv.push("--out-dir", args.out_dir);
  if (typeof args.scale === "number") argv.push("--scale", String(args.scale));
  return runPython("web/render_views.py", argv);
}

/** qa_assert: machine checks over a renders directory. */
export function handleQaAssert(args: HandlerArgs): ToolResult {
  if (!nonEmptyString(args.renders_dir)) {
    return fail("qa_assert rejected: 'renders_dir' must be a non-empty string.");
  }
  if (!stringArray(args.labels) || args.labels.length === 0) {
    return fail("qa_assert rejected: 'labels' must be a non-empty array of strings.");
  }
  const argv = ["--renders", args.renders_dir, "--labels", args.labels.join(","), "--json"];
  if (nonEmptyString(args.engine)) argv.push("--engine", args.engine);
  if (nonEmptyString(args.baseline_dir)) argv.push("--baseline", args.baseline_dir);
  return runPython("qa/run_qa.py", argv);
}

/** export_scene: zip (or a single html/png) of a built scene. */
export function handleExportScene(args: HandlerArgs): ToolResult {
  if (!nonEmptyString(args.scene)) {
    return fail("export_scene rejected: 'scene' must be a non-empty string (the scene directory).");
  }
  const format = args.format;
  if (format !== "blend" && format !== "html" && format !== "png" && format !== "zip") {
    return fail("export_scene rejected: 'format' must be 'zip', 'html', 'png', or 'blend'.");
  }
  if (format === "blend") {
    return fail(
      "export_scene: a .blend comes from build with backend 'blender', not from export. " +
        "Export the scene directory as 'zip' to ship everything it holds.",
      { scene: args.scene },
    );
  }
  const argv = ["--scene-dir", args.scene, "--format", format];
  if (nonEmptyString(args.out)) argv.push("--out", args.out);
  if (nonEmptyString(args.view)) argv.push("--view", args.view);
  return runPython("tools/export_scene.py", argv);
}

/** Dispatch by tool name. Unknown tools throw (fail-closed), like zero-vision. */
export function handleTool(name: string, args: HandlerArgs): ToolResult {
  switch (name) {
    case "brief":
      return handleBrief(args);
    case "spec_compile":
      return handleSpecCompile(args);
    case "build":
      return handleBuild(args);
    case "views":
      return handleViews(args);
    case "qa_assert":
      return handleQaAssert(args);
    case "export_scene":
      return handleExportScene(args);
    default:
      throw new Error(`unknown tool ${name}`);
  }
}
