import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(here, "..");

export function ensureData({
  publicDataDir = path.join(webRoot, "public", "data"),
  fallbackDataDir = path.join(webRoot, "deploy-data", "data"),
} = {}) {
  if (existsSync(path.join(publicDataDir, "meta.json"))) return "existing";
  if (!existsSync(path.join(fallbackDataDir, "meta.json"))) {
    throw new Error(`fallback data missing: ${fallbackDataDir}`);
  }
  rmSync(publicDataDir, { recursive: true, force: true });
  mkdirSync(path.dirname(publicDataDir), { recursive: true });
  cpSync(fallbackDataDir, publicDataDir, { recursive: true });
  return "fallback";
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const result = ensureData();
  console.log(`atlas data: ${result}`);
}
