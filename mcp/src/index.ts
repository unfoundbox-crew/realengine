#!/usr/bin/env node
// code-to-3d MCP server.
//
// Tiny surface: exactly 6 verbs. The skill calls these; the agent never sees
// raw bpy/GL. Each one runs the Python step that owns the job (see
// ./handlers.js) and returns its JSON receipt; a step whose dependency is
// missing returns ok:false naming it, never a silent fallback.
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { handleTool, type HandlerArgs } from "./handlers.js";

const text = (s: string) => ({ content: [{ type: "text" as const, text: s }] });

export function listTools() {
  return [
    {
      name: "brief",
      description:
        "Record a scene brief and draft SCENE_SPEC.md from it (the one step that calls a model). Call this first, when the skill has intent words and needs a spec to approve. Returns brief_id, the spec path, and both hashes; the draft is rejected unless it passes the validator and parses complete.",
      inputSchema: {
        type: "object",
        properties: {
          prompt: { type: "string", description: "What to build, in words." },
          refs: {
            type: "array",
            items: { type: "string" },
            description: "Reference paths or URLs to mention to the drafter.",
          },
          store: {
            type: "string",
            description: "Brief store directory (default: .realengine under the repo).",
          },
          model: {
            type: "string",
            description: "Model id override, e.g. gemini-3.7-flash for a cheap draft.",
          },
        },
        required: ["prompt"],
      },
    },
    {
      name: "spec_compile",
      description:
        "Compile an approved SCENE_SPEC.md into the pinned build JSON both backends consume. Offline, deterministic, no model. Call this after Human Gate 1, or any time you need the hashes for a spec.",
      inputSchema: {
        type: "object",
        properties: {
          brief_id: { type: "string", description: "Compile the spec stored under this brief." },
          spec_path: { type: "string", description: "Compile a SCENE_SPEC.md at this path." },
          store: { type: "string", description: "Brief store directory, with brief_id." },
          out_dir: { type: "string", description: "Where to write build.json." },
        },
      },
    },
    {
      name: "build",
      description:
        "Build an approved spec into a scene. backend 'web' writes a standalone Three.js HTML page plus build.json and views.json; backend 'blender' compiles the spec then drives headless Blender to a .blend (needs Blender installed). Call this after Human Gate 1.",
      inputSchema: {
        type: "object",
        properties: {
          spec_path: { type: "string" },
          backend: { type: "string", enum: ["blender", "web"] },
          out_dir: { type: "string", description: "Scene directory (default: out/scene)." },
          engine: { type: "string", description: "Blender render engine override." },
          samples: { type: "number", description: "Blender render samples." },
          res_scale: { type: "number", description: "Scale every view's resolution." },
        },
        required: ["spec_path", "backend"],
      },
    },
    {
      name: "views",
      description:
        "Render PNGs of the named camera views of a built web scene, via headless Chromium. Call this after build, when the QA loop or the human eye needs frames. Without a headless browser it renders nothing and returns the requirement plus the ?view= URLs any browser can drive.",
      inputSchema: {
        type: "object",
        properties: {
          scene: { type: "string", description: "Scene directory holding scene.html and views.json." },
          cameras: {
            type: "array",
            items: { type: "string" },
            description: "Camera names to render (default: every view in the manifest).",
          },
          out_dir: { type: "string", description: "Where to write PNGs (default: <scene>/renders)." },
          scale: { type: "number", description: "Resolution multiplier, 1.0 = the manifest size." },
        },
        required: ["scene"],
      },
    },
    {
      name: "qa_assert",
      description:
        "Run the machine checks over a renders directory: every expected label must be legible to OCR, and optionally every frame must match a baseline's dimensions. Call this after views, before showing anything to the human eye.",
      inputSchema: {
        type: "object",
        properties: {
          renders_dir: { type: "string" },
          labels: { type: "array", items: { type: "string" } },
          engine: {
            type: "string",
            description: "zero-vision OCR engine (default tesseract; apple-vision reads these renders better on macOS).",
          },
          baseline_dir: { type: "string", description: "Second renders dir for views_match." },
        },
        required: ["renders_dir", "labels"],
      },
    },
    {
      name: "export_scene",
      description:
        "Export a verified scene directory: 'zip' bundles html + build.json + SCENE_SPEC.md + views.json + renders with a sha256 manifest; 'html' or 'png' copies out a single file. Call this last, after qa_assert and Human Gate 2.",
      inputSchema: {
        type: "object",
        properties: {
          scene: { type: "string", description: "Scene directory." },
          format: { type: "string", enum: ["zip", "html", "png", "blend"] },
          out: { type: "string", description: "Output path." },
          view: { type: "string", description: "Which render, for format 'png'." },
        },
        required: ["scene", "format"],
      },
    },
  ];
}

export async function startMcp(): Promise<void> {
  const server = new Server({ name: "code-to-3d-mcp", version: "0.2.0" }, { capabilities: { tools: {} } });

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: listTools(),
  }));

  server.setRequestHandler(CallToolRequestSchema, async (req) => {
    const args = (req.params.arguments ?? {}) as HandlerArgs;
    switch (req.params.name) {
      case "brief":
      case "spec_compile":
      case "build":
      case "views":
      case "qa_assert":
      case "export_scene": {
        const result = handleTool(req.params.name, args);
        return text(JSON.stringify(result, null, 2));
      }
      default:
        throw new Error(`unknown tool ${req.params.name}`);
    }
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);
}

const isMain = process.argv[1]?.endsWith("index.js") || process.argv[1]?.endsWith("index.ts");
if (isMain) {
  startMcp().catch((err) => {
    process.stderr.write(String(err) + "\n");
    process.exit(1);
  });
}
