import fs from "node:fs/promises";
import path from "node:path";

/**
 * n8n import expects certain top-level fields. Some of our workflow JSONs are "partial"
 * and miss required fields like `active`, which causes SQLITE_CONSTRAINT errors.
 *
 * This script normalizes all *.json under a directory (recursive) to be importable.
 *
 * Usage:
 *   node normalize-workflows.mjs /path/to/workflows
 */

async function listJsonFiles(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await listJsonFiles(full)));
      continue;
    }
    if (entry.isFile() && entry.name.toLowerCase().endsWith(".json")) files.push(full);
  }

  return files;
}

function isPlainObject(value) {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function normalizeWorkflowJson(raw, filePath) {
  if (!isPlainObject(raw)) throw new Error(`Not an object: ${filePath}`);
  if (!Array.isArray(raw.nodes)) throw new Error(`Missing nodes[]: ${filePath}`);
  if (!raw.name || typeof raw.name !== "string") throw new Error(`Missing name: ${filePath}`);

  // Ensure required top-level properties exist and are valid
  if (typeof raw.active !== "boolean") raw.active = false;
  if (!isPlainObject(raw.settings)) raw.settings = { executionOrder: "v1" };
  if (!isPlainObject(raw.connections)) raw.connections = {};
  if (!Array.isArray(raw.tags)) raw.tags = [];

  // Prevent import from trying to "update" non-existent workflows by stale IDs
  // (If a workflow file ever got an exported `id`, remove it.)
  if ("id" in raw && typeof raw.id !== "undefined") delete raw.id;
  if ("versionId" in raw && typeof raw.versionId !== "undefined") delete raw.versionId;

  return raw;
}

async function main() {
  const workflowsDir = process.argv[2];
  if (!workflowsDir) {
    console.error("Usage: node normalize-workflows.mjs /path/to/workflows");
    process.exit(2);
  }

  const files = await listJsonFiles(workflowsDir);
  if (files.length === 0) {
    console.log(`No workflow JSON files found under: ${workflowsDir}`);
    return;
  }

  let normalized = 0;
  let skipped = 0;

  for (const file of files) {
    try {
      const text = await fs.readFile(file, "utf-8");
      const json = JSON.parse(text);
      const next = normalizeWorkflowJson(json, file);
      await fs.writeFile(file, JSON.stringify(next, null, 2) + "\n", "utf-8");
      normalized += 1;
    } catch (err) {
      skipped += 1;
      console.warn(`[normalize-workflows] Skipping ${file}: ${err?.message ?? String(err)}`);
    }
  }

  console.log(`[normalize-workflows] Normalized: ${normalized}, Skipped: ${skipped}`);
}

main().catch((err) => {
  console.error("[normalize-workflows] Fatal:", err);
  process.exit(1);
});


