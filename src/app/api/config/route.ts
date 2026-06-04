import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";
import { parse as parseYaml } from "yaml";

// Read fresh on every request so editing config.yaml doesn't require a restart.
export const dynamic = "force-dynamic";

/**
 * Resolves the default stream URL for the frontend, in priority order:
 *   1. A `config.yaml` / `config.yml` at the project root (key: `streamUrl`)
 *   2. The `NEXT_PUBLIC_DEFAULT_STREAM_URL` / `DEFAULT_STREAM_URL` env var
 *   3. null (the client then falls back to its built-in default)
 *
 * Also resolves an optional default Comfy workflow to pre-load in the UI from
 * the `NEXT_PUBLIC_DEFAULT_WORKFLOW` / `DEFAULT_WORKFLOW` env var, which points
 * at a workflow JSON file (path relative to the project root, e.g.
 * `workflows/final_260603.json`). The browser can't read the filesystem, so we
 * read and parse it server-side and hand the client `{ name, prompt }`.
 */
export async function GET() {
  let streamUrl: string | null = null;

  for (const name of ["config.yaml", "config.yml"]) {
    try {
      const raw = await fs.readFile(path.join(process.cwd(), name), "utf8");
      const data = parseYaml(raw) ?? {};
      if (data && typeof data.streamUrl === "string" && data.streamUrl.trim()) {
        streamUrl = data.streamUrl.trim();
        break;
      }
    } catch {
      // File missing or unparseable — fall through to the next source.
    }
  }

  if (!streamUrl) {
    streamUrl =
      process.env.NEXT_PUBLIC_DEFAULT_STREAM_URL ||
      process.env.DEFAULT_STREAM_URL ||
      null;
  }

  let workflow: { name: string; prompt: unknown } | null = null;
  const workflowPath =
    process.env.NEXT_PUBLIC_DEFAULT_WORKFLOW || process.env.DEFAULT_WORKFLOW;
  if (workflowPath && workflowPath.trim()) {
    const rel = workflowPath.trim();
    const abs = path.isAbsolute(rel) ? rel : path.join(process.cwd(), rel);
    try {
      const raw = await fs.readFile(abs, "utf8");
      workflow = { name: path.basename(rel), prompt: JSON.parse(raw) };
    } catch {
      // Missing or invalid workflow file — start in passthrough mode.
    }
  }

  return NextResponse.json({ streamUrl, workflow });
}
