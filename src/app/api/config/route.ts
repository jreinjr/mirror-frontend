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

  return NextResponse.json({ streamUrl });
}
