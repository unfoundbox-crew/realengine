// Live end-to-end pass: brief -> spec_compile -> build(web), through the
// real MCP stdio transport, against an actual LiteLLM proxy -- no
// REALENGINE_LLM_STUB. This is the one test in the suite that spends a real
// model call and needs a private network + Doppler secrets, so it is
// gated: skipped unless REALENGINE_LIVE=1, and the hermetic suite (smoke,
// tools) never depends on it or on this env var.
//
// Run it explicitly:
//   doppler run --project unfoundbox --config dev_personal -- \
//     env REALENGINE_LIVE=1 node mcp/test/live.test.js
//
// 2026-09-12: on the current proxy, requests for claude-sonnet-5 and
// claude-fable-5 both 500 (Bedrock models not enabled), gemini-3.7-flash is
// out of daily quota, and claude-sonnet-4-6 -- the default this test relies
// on -- actually comes back with "model": "openai/gpt-oss-120b" and a
// gpt-oss-style reasoning field: this proxy currently serves that id via a
// groq gpt-oss-120b fallback, not a live Claude backend. This test asserts
// the tool path and the receipt shape, not which backend model answered.
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const MCP_DIR = path.resolve(HERE, "..");
const REPO_ROOT = path.resolve(MCP_DIR, "..");
const SERVER = path.join(MCP_DIR, "dist", "index.js");

if (process.env.REALENGINE_LIVE !== "1") {
  console.log("SKIP: live MCP test (set REALENGINE_LIVE=1 to run against the real proxy)");
  process.exit(0);
}

const work = fs.mkdtempSync(path.join(os.tmpdir(), "realengine-live-"));
const store = path.join(work, "store");
const sceneDir = path.join(work, "scene");

const env = { ...process.env, REALENGINE_ROOT: REPO_ROOT, REALENGINE_PYTHON: process.env.REALENGINE_PYTHON ?? "python3" };
delete env.REALENGINE_LLM_STUB; // this test's whole point is to skip the stub

const client = new Client({ name: "realengine-live-test", version: "0" }, { capabilities: {} });
const transport = new StdioClientTransport({ command: process.execPath, args: [SERVER], env, stderr: "inherit" });
await client.connect(transport);

const call = async (name, args) => {
  const res = await client.callTool({ name, arguments: args });
  assert.equal(res.content?.[0]?.type, "text", `${name} must answer with text`);
  return JSON.parse(res.content[0].text);
};

const brief = await call("brief", {
  prompt: "a minimalist desk lamp with a 30 cm arm and a warm bulb, three camera views",
  store,
});
assert.equal(brief.ok, true, `live brief failed: ${JSON.stringify(brief)}`);
assert.equal(brief.source, "llm", "a live draft must be labelled source: llm, not stub");
assert.ok(fs.existsSync(brief.spec_path), "brief must write a SCENE_SPEC.md");
assert.ok(brief.objects >= 1 && brief.cameras.length >= 1, "the drafted spec must parse complete");

const compiled = await call("spec_compile", { brief_id: brief.brief_id, store });
assert.equal(compiled.ok, true, `spec_compile failed: ${JSON.stringify(compiled)}`);
assert.equal(compiled.build_sha256, brief.build_sha256, "brief and spec_compile must pin the same hash");
assert.equal(compiled.offline, true);

const build = await call("build", { spec_path: brief.spec_path, backend: "web", out_dir: sceneDir });
assert.equal(build.ok, true, `web build failed: ${JSON.stringify(build)}`);
assert.equal(build.build_sha256, brief.build_sha256);
assert.ok(fs.existsSync(path.join(sceneDir, "scene.html")), "build must write scene.html");
assert.ok(fs.statSync(path.join(sceneDir, "scene.html")).size > 1000);

await client.close();
fs.rmSync(work, { recursive: true, force: true });
console.log(
  `PASS: live MCP run (brief_id=${brief.brief_id} model=${brief.model} ` +
    `objects=${brief.objects} build_sha256=${brief.build_sha256.slice(0, 12)}…)`,
);
