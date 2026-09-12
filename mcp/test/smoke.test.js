// Fast unit smoke over the handler layer: the tool list, argument validation,
// and the dispatch contract. No subprocess, no filesystem, no network.
// The end-to-end pass is test/tools.test.js, which drives the real transport.
import assert from "node:assert/strict";
import { listTools } from "../dist/index.js";
import { handleTool } from "../dist/handlers.js";

// Test 1: listTools returns the 6 verbs, in order
const tools = listTools();
assert.equal(tools.length, 6, "Must export exactly 6 tools");
const expected = ["brief", "spec_compile", "build", "views", "qa_assert", "export_scene"];
assert.deepEqual(tools.map((t) => t.name), expected);

// Test 2: every required property is declared in its own schema
for (const tool of tools) {
  assert.equal(tool.inputSchema.type, "object", `${tool.name} schema must be an object`);
  for (const req of tool.inputSchema.required ?? []) {
    assert.ok(tool.inputSchema.properties[req], `${tool.name} requires undeclared '${req}'`);
  }
}

// Test 3: argument validation happens before any work is attempted
const badBuild = handleTool("build", {});
assert.equal(badBuild.ok, false);
assert.match(badBuild.error, /'spec_path' must be a non-empty string/);

const badBackend = handleTool("build", { spec_path: "SCENE_SPEC.md", backend: "unity" });
assert.equal(badBackend.ok, false);
assert.match(badBackend.error, /'backend' must be 'blender' or 'web'/);

const badViews = handleTool("views", { scene: "out/scene", cameras: "CAM_Master" });
assert.equal(badViews.ok, false);
assert.match(badViews.error, /'cameras' must be an array of strings/);

const badQa = handleTool("qa_assert", { renders_dir: "out/renders", labels: [] });
assert.equal(badQa.ok, false);
assert.match(badQa.error, /'labels' must be a non-empty array/);

const badExport = handleTool("export_scene", { scene: "out/scene", format: "usd" });
assert.equal(badExport.ok, false);
assert.match(badExport.error, /'format' must be/);

// Test 4: a .blend is a build output, not an export format — say so, don't fake it
const blendExport = handleTool("export_scene", { scene: "out/scene", format: "blend" });
assert.equal(blendExport.ok, false);
assert.match(blendExport.error, /build with backend 'blender'/);

// Test 5: unknown tool throws
assert.throws(() => handleTool("unknown_tool", {}));

console.log("PASS: MCP smoke tests (6 tools, schemas self-consistent, args validated)");
