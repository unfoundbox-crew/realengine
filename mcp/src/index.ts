#!/usr/bin/env node
// code-to-3d MCP server — Wave 1 sketch.
//
// Tiny surface: exactly 6 verbs. The skill calls these; the agent never
// sees raw bpy/GL. Every handler fails closed (see ./handlers.js) until
// Wave 2 builds the backends. Shape mirrors zero-vision src/mcp.ts:
// listTools + handler switch + fail-closed errors.
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
        "Record a natural-language scene prompt (plus optional ref paths/URLs) for spec compilation. Call this first, when the skill has intent words and needs a brief_id to compile.",
      inputSchema: {
        type: "object",
        properties: {
          prompt: { type: "string" },
          refs: { type: "array", items: { type: "string" } },
        },
        required: ["prompt"],
      },
    },
    {
      name: "spec_compile",
      description:
        "Compile a recorded brief into SCENE_SPEC.md (the contract both agents and humans read). Call this after brief, before Human Gate 1 approves the spec.",
      inputSchema: {
        type: "object",
        properties: {
          brief_id: { type: "string" },
        },
        required: ["brief_id"],
      },
    },
    {
      name: "build",
      description:
        "Build an approved spec into a deterministic scene on the blender or web backend. Call this after Human Gate 1, when SCENE_SPEC.md is approved and a .blend/HTML scene is needed.",
      inputSchema: {
        type: "object",
        properties: {
          spec_path: { type: "string" },
          backend: { type: "string", enum: ["blender", "web"] },
        },
        required: ["spec_path", "backend"],
      },
    },
    {
      name: "views",
      description:
        "Render QA views of a built scene from the named cameras. Call this after build, when the skill needs PNGs for the machine QA loop or Human Gate 2 (the eye).",
      inputSchema: {
        type: "object",
        properties: {
          scene: { type: "string" },
          cameras: { type: "array", items: { type: "string" } },
        },
        required: ["scene", "cameras"],
      },
    },
    {
      name: "qa_assert",
      description:
        "Run machine-checkable asserts (legible, match, no-overlap) over a renders directory. Call this after views, when the skill needs a pass/fail verdict before showing anything to the human eye.",
      inputSchema: {
        type: "object",
        properties: {
          renders_dir: { type: "string" },
          labels: { type: "array", items: { type: "string" } },
        },
        required: ["renders_dir", "labels"],
      },
    },
    {
      name: "export_scene",
      description:
        "Export a verified scene to blend, self-contained html, or snapshot png. Call this last, after qa_assert passes and Human Gate 2 approves, when the skill needs the shippable artifact.",
      inputSchema: {
        type: "object",
        properties: {
          scene: { type: "string" },
          format: { type: "string", enum: ["blend", "html", "png"] },
        },
        required: ["scene", "format"],
      },
    },
  ];
}

export async function startMcp(): Promise<void> {
  const server = new Server({ name: "code-to-3d-mcp", version: "0.0.0" }, { capabilities: { tools: {} } });

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
