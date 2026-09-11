// code-to-3d MCP handlers — Wave 1 sketch.
//
// Every handler validates its args and then fails closed with a named
// reason: the backend module it names does not exist yet. Nothing here
// pretends to work; nothing touches Blender, renders, or the network.
// Shape mirrors unfoundbox-crew/zero-vision src/mcp.ts (fail-closed errors).

export type FailClosed = { ok: false; error: string };
export type HandlerArgs = Record<string, unknown>;

const fail = (error: string): FailClosed => ({ ok: false, error });

function nonEmptyString(v: unknown): v is string {
  return typeof v === "string" && v.trim().length > 0;
}

function stringArray(v: unknown): v is string[] {
  return Array.isArray(v) && v.every((x) => typeof x === "string");
}

/** brief: record a natural-language prompt (+ optional refs) for spec compilation. */
export function handleBrief(args: HandlerArgs): FailClosed {
  if (!nonEmptyString(args.prompt)) {
    return fail("brief rejected: 'prompt' must be a non-empty string.");
  }
  if (args.refs !== undefined && !stringArray(args.refs)) {
    return fail("brief rejected: 'refs' must be an array of strings when provided.");
  }
  return fail(
    "brief store lands in Wave 2 (spec/ prompt→spec compiler): prompt accepted for validation only, nothing persisted.",
  );
}

/** spec_compile: compile a recorded brief into SCENE_SPEC.md. */
export function handleSpecCompile(args: HandlerArgs): FailClosed {
  if (!nonEmptyString(args.brief_id)) {
    return fail("spec_compile rejected: 'brief_id' must be a non-empty string.");
  }
  return fail(
    "spec compiler lands in Wave 2 (spec/ schema + validator + prompt→spec compiler): no SCENE_SPEC.md produced.",
  );
}

/** build: build a spec into a scene on the blender or web backend. */
export function handleBuild(args: HandlerArgs): FailClosed {
  if (!nonEmptyString(args.spec_path)) {
    return fail("build rejected: 'spec_path' must be a non-empty string.");
  }
  if (args.backend !== "blender" && args.backend !== "web") {
    return fail("build rejected: 'backend' must be 'blender' or 'web'.");
  }
  const mod = args.backend === "blender" ? "blender/ bpy library + build.py" : "web/ Three.js template";
  return fail(`blender/web backend lands in Wave 2 (${mod}): no scene built from '${args.spec_path}'.`);
}

/** views: render QA views of a scene from the given cameras. */
export function handleViews(args: HandlerArgs): FailClosed {
  if (!nonEmptyString(args.scene)) {
    return fail("views rejected: 'scene' must be a non-empty string.");
  }
  if (!stringArray(args.cameras) || args.cameras.length === 0) {
    return fail("views rejected: 'cameras' must be a non-empty array of strings.");
  }
  return fail(
    "camera/QA view renderer lands in Wave 2 (blender/ cameras + labels + QA views): no views rendered.",
  );
}

/** qa_assert: run machine-checkable asserts over a renders directory. */
export function handleQaAssert(args: HandlerArgs): FailClosed {
  if (!nonEmptyString(args.renders_dir)) {
    return fail("qa_assert rejected: 'renders_dir' must be a non-empty string.");
  }
  if (!stringArray(args.labels) || args.labels.length === 0) {
    return fail("qa_assert rejected: 'labels' must be a non-empty array of strings.");
  }
  return fail(
    "QA assert loop lands in Wave 2 (qa/ zero-vision asserts): no asserts evaluated.",
  );
}

/** export_scene: export a scene to blend, html, or png. */
export function handleExportScene(args: HandlerArgs): FailClosed {
  if (!nonEmptyString(args.scene)) {
    return fail("export_scene rejected: 'scene' must be a non-empty string.");
  }
  if (args.format !== "blend" && args.format !== "html" && args.format !== "png") {
    return fail("export_scene rejected: 'format' must be 'blend', 'html', or 'png'.");
  }
  const mod =
    args.format === "blend"
      ? "blender/ .blend writer"
      : args.format === "html"
        ? "web/ self-contained HTML writer"
        : "blender/ + web/ snapshot PNG writer";
  return fail(`scene exporter lands in Wave 2 (${mod}): nothing exported.`);
}

/** Dispatch by tool name. Unknown tools throw (fail-closed), like zero-vision. */
export function handleTool(name: string, args: HandlerArgs): FailClosed {
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
