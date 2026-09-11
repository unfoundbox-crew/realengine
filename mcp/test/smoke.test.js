import assert from "node:assert/strict";
import { listTools } from "../dist/index.js";
import { handleTool } from "../dist/handlers.js";

// Test 1: listTools returns 6 verbs
const tools = listTools();
assert.equal(tools.length, 6, "Must export exactly 6 tools");
const expected = ["brief", "spec_compile", "build", "views", "qa_assert", "export_scene"];
assert.deepEqual(tools.map((t) => t.name), expected);

// Test 2: validation error when missing args
const badBuild = handleTool("build", {});
assert.equal(badBuild.ok, false);
assert.match(badBuild.error, /'spec_path' must be a non-empty string/);

// Test 3: fail-closed with clear message on valid args
const goodBuild = handleTool("build", { spec_path: "SCENE_SPEC.md", backend: "web" });
assert.equal(goodBuild.ok, false);
assert.match(goodBuild.error, /blender\/web backend lands in Wave 2/);

// Test 4: unknown tool throws
assert.throws(() => handleTool("unknown_tool", {}));

console.log("PASS: MCP smoke tests (6 tools verified, fail-closed handlers checked)");
