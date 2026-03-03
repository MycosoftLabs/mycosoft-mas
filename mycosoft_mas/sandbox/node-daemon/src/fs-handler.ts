/**
 * File System Handler -- sandboxed file operations restricted to /workspace.
 */

import * as nodefs from "fs/promises";
import * as path from "path";

const WORKSPACE_ROOT = "/workspace";

function safePath(requestedPath: string): string {
  const resolved = path.resolve(WORKSPACE_ROOT, requestedPath);
  if (!resolved.startsWith(WORKSPACE_ROOT)) {
    throw new Error("Path traversal denied: must stay within /workspace");
  }
  return resolved;
}

export class FsHandler {
  async handle(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
    const action = payload.action as string;

    switch (action) {
      case "read":
        return this.readFile(payload.path as string);
      case "write":
        return this.writeFile(payload.path as string, payload.content as string);
      case "list":
        return this.listDir(payload.path as string);
      case "delete":
        return this.deleteFile(payload.path as string);
      case "exists":
        return this.exists(payload.path as string);
      default:
        return { error: `Unknown fs action: ${action}` };
    }
  }

  private async readFile(filePath: string): Promise<Record<string, unknown>> {
    const full = safePath(filePath);
    const content = await nodefs.readFile(full, "utf-8");
    return { content, path: filePath, size: content.length };
  }

  private async writeFile(filePath: string, content: string): Promise<Record<string, unknown>> {
    const full = safePath(filePath);
    await nodefs.mkdir(path.dirname(full), { recursive: true });
    await nodefs.writeFile(full, content, "utf-8");
    return { ok: true, path: filePath, size: content.length };
  }

  private async listDir(dirPath: string): Promise<Record<string, unknown>> {
    const full = safePath(dirPath || ".");
    const entries = await nodefs.readdir(full, { withFileTypes: true });
    return {
      entries: entries.map((e) => ({
        name: e.name,
        type: e.isDirectory() ? "dir" : "file",
      })),
      path: dirPath || ".",
    };
  }

  private async deleteFile(filePath: string): Promise<Record<string, unknown>> {
    const full = safePath(filePath);
    await nodefs.rm(full, { recursive: true, force: true });
    return { ok: true, path: filePath };
  }

  private async exists(filePath: string): Promise<Record<string, unknown>> {
    const full = safePath(filePath);
    try {
      await nodefs.access(full);
      return { exists: true, path: filePath };
    } catch {
      return { exists: false, path: filePath };
    }
  }
}
