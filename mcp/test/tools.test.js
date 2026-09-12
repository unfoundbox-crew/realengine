// Hermetic end-to-end test: every tool driven through the MCP stdio
// transport, with stubs for everything that would reach the network or a
// machine-specific dependency.
//
// Stubs, all deterministic:
//   REALENGINE_LLM_STUB    the drafter returns a golden SCENE_SPEC.md
//   REALENGINE_BLENDER     a path that does not exist -> the "no Blender"
//                          branch, so the receipt shape is asserted without
//                          needing Blender anywhere
//   views/qa_assert        pointed at inputs with no manifest and no PNGs,
//                          so no browser and no OCR subprocess run
//
// What this proves: the tool list, the schemas and the handlers agree, and
// each tool returns a structured receipt through a real client.

import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

import { listTools } from "../dist/index.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const MCP_DIR = path.resolve(HERE, "..");
const REPO_ROOT = path.resolve(MCP_DIR, "..");
const SERVER = path.join(MCP_DIR, "dist", "index.js");
const GOLDEN_SPEC = path.join(REPO_ROOT, "tests", "golden", "brain.emitted.md");
const PINNED = JSON.parse(
  fs.readFileSync(path.join(REPO_ROOT, "tests", "golden", "brain.hashes.json"), "utf8"),
);

const work = fs.mkdtempSync(path.join(os.tmpdir(), "realengine-mcp-"));
const store = path.join(work, "store");
const sceneDir = path.join(work, "scene");
const emptyDir = path.join(work, "empty");
fs.mkdirSync(emptyDir, { recursive: true });

const env = {
  ...process.env,
  REALENGINE_ROOT: REPO_ROOT,
  REALENGINE_PYTHON: process.env.REALENGINE_PYTHON ?? "python3",
  REALENGINE_LLM_STUB: GOLDEN_SPEC,
  REALENGINE_BLENDER: path.join(work, "no-such-blender"),
};

const client = new Client({ name: "realengine-test", version: "0" }, { capabilities: {} });
const transport = new StdioClientTransport({
  command: process.execPath,
  args: [SERVER],
  env,
  stderr: "ignore",
});
await client.connect(transport);

const call = async (name, args) => {
  const res = await client.callTool({ name, arguments: args });
  assert.equal(res.content?.[0]?.type, "text", `${name} must answer with text`);
  return JSON.parse(res.content[0].text);
};

// ---------------------------------------------------------------- tool list
const listed = await client.listTools();
const names = listed.tools.map((t) => t.name);
assert.deepEqual(names, ["brief", "spec_compile", "build", "views", "qa_assert", "export_scene"]);
assert.deepEqual(
  names,
  listTools().map((t) => t.name),
  "the exported list and the served list must agree",
);
for (const tool of listed.tools) {
  assert.ok(tool.description && tool.description.length > 40, `${tool.name} needs a real description`);
  assert.equal(tool.inputSchema.type, "object");
  for (const req of tool.inputSchema.required ?? []) {
    assert.ok(tool.inputSchema.properties[req], `${tool.name}.${req} is required but not declared`);
  }
}

// ------------------------------------------------------------------- brief
const badBrief = await call("brief", {});
assert.equal(badBrief.ok, false);
assert.match(badBrief.error, /'prompt' must be a non-empty string/);

const brief = await call("brief", {
  prompt: "the human brain as a layered predictive-control system",
  refs: ["examples/brain/README.md"],
  store,
});
assert.equal(brief.ok, true, `brief failed: ${JSON.stringify(brief)}`);
assert.equal(brief.source, "stub", "a stubbed draft must be labelled as a stub");
assert.equal(brief.build_sha256, PINNED.build_sha256);
assert.ok(fs.existsSync(brief.spec_path), "brief must write a SCENE_SPEC.md");

// ------------------------------------------------------------- spec_compile
const noArgs = await call("spec_compile", {});
assert.equal(noArgs.ok, false);
assert.match(noArgs.error, /pass 'brief_id' or 'spec_path'/);

const bothArgs = await call("spec_compile", { brief_id: brief.brief_id, spec_path: GOLDEN_SPEC });
assert.equal(bothArgs.ok, false);
assert.match(bothArgs.error, /not both/);

const compiled = await call("spec_compile", { brief_id: brief.brief_id, store });
assert.equal(compiled.ok, true, `spec_compile failed: ${JSON.stringify(compiled)}`);
assert.equal(compiled.build_sha256, PINNED.build_sha256, "the hash is the pin");
assert.equal(compiled.offline, true);
assert.ok(compiled.cameras.includes("CAM_Master"));

// second run, same inputs, same hash: deterministic
const again = await call("spec_compile", { spec_path: brief.spec_path });
assert.equal(again.build_sha256, compiled.build_sha256);

// ------------------------------------------------------------------- build
const badBackend = await call("build", { spec_path: brief.spec_path, backend: "unity" });
assert.equal(badBackend.ok, false);
assert.match(badBackend.error, /'backend' must be 'blender' or 'web'/);

const web = await call("build", { spec_path: brief.spec_path, backend: "web", out_dir: sceneDir });
assert.equal(web.ok, true, `web build failed: ${JSON.stringify(web)}`);
assert.equal(web.backend, "web");
assert.equal(web.build_sha256, PINNED.build_sha256);
for (const f of ["scene.html", "build.json", "views.json", "SCENE_SPEC.md"]) {
  assert.ok(fs.existsSync(path.join(sceneDir, f)), `web build must write ${f}`);
}
const html = fs.readFileSync(path.join(sceneDir, "scene.html"), "utf8");
assert.ok(!html.includes("{{"), "no unbound slot may survive into the page");
assert.ok(html.includes("CAM_Master"), "the page carries the spec's cameras");
assert.ok(html.includes("Thalamus"), "the page carries the spec's labels");
const manifest = JSON.parse(fs.readFileSync(path.join(sceneDir, "views.json"), "utf8"));
assert.equal(manifest.views.length, web.cameras.length);
for (const row of manifest.views) {
  assert.match(row.url, /^scene\.html\?view=CAM_/, "every view is drivable by URL");
  assert.ok(row.res_x > 0 && row.res_y > 0);
}

// Blender, with the binary deliberately absent: a named requirement, not a lie.
const blender = await call("build", {
  spec_path: brief.spec_path,
  backend: "blender",
  out_dir: path.join(work, "blender-scene"),
});
assert.equal(blender.ok, false);
assert.match(String(blender.requirement), /Blender/i);
assert.equal(blender.build_sha256, PINNED.build_sha256, "the spec still compiled");

// ------------------------------------------------------------------- views
const badViews = await call("views", { scene: sceneDir, cameras: "CAM_Master" });
assert.equal(badViews.ok, false);
assert.match(badViews.error, /'cameras' must be an array/);

const noManifest = await call("views", { scene: emptyDir });
assert.equal(noManifest.ok, false);
assert.match(String(noManifest.error), /no views\.json/);

// --------------------------------------------------------------- qa_assert
const badQa = await call("qa_assert", { renders_dir: sceneDir, labels: [] });
assert.equal(badQa.ok, false);
assert.match(badQa.error, /'labels' must be a non-empty array/);

const noPngs = await call("qa_assert", { renders_dir: emptyDir, labels: ["Thalamus"] });
assert.equal(noPngs.ok, false);
assert.match(String(noPngs.error), /no PNGs/);
assert.deepEqual(noPngs.labels, ["Thalamus"]);

// ------------------------------------------------------------ export_scene
const badFormat = await call("export_scene", { scene: sceneDir, format: "gltf" });
assert.equal(badFormat.ok, false);
assert.match(badFormat.error, /'format' must be/);

const zip = await call("export_scene", { scene: sceneDir, format: "zip", out: path.join(work, "scene.zip") });
assert.equal(zip.ok, true, `export failed: ${JSON.stringify(zip)}`);
assert.ok(zip.entries.includes("scene.html"));
assert.ok(zip.entries.includes("SCENE_SPEC.md"));
assert.ok(zip.entries.includes("manifest.json"));
assert.ok(fs.statSync(zip.path).size > 1000);

const onlyHtml = await call("export_scene", { scene: sceneDir, format: "html", out: path.join(work, "one.html") });
assert.equal(onlyHtml.ok, true);
assert.equal(onlyHtml.sha256.length, 64);

const noPng = await call("export_scene", { scene: sceneDir, format: "png" });
assert.equal(noPng.ok, false);
assert.match(String(noPng.error), /no PNGs/);

// ------------------------------------------------------------ unknown tool
await assert.rejects(() => client.callTool({ name: "no_such_tool", arguments: {} }));

await client.close();
fs.rmSync(work, { recursive: true, force: true });
console.log("PASS: MCP tool tests (6 tools driven through the stdio transport)");
