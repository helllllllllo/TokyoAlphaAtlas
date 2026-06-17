import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { ensureData } from "./ensure-data.mjs";

function tmpRoot() {
  return mkdtempSync(path.join(tmpdir(), "atlas-data-"));
}

describe("ensureData", () => {
  it("copies fallback data when public data is absent", () => {
    const root = tmpRoot();
    try {
      const publicDataDir = path.join(root, "public", "data");
      const fallbackDataDir = path.join(root, "deploy-data", "data");
      mkdirSync(fallbackDataDir, { recursive: true });
      writeFileSync(path.join(fallbackDataDir, "meta.json"), '{"schema_version":1}');

      const result = ensureData({ publicDataDir, fallbackDataDir });

      expect(result).toBe("fallback");
      expect(readFileSync(path.join(publicDataDir, "meta.json"), "utf8")).toBe('{"schema_version":1}');
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  it("keeps existing public data so local full exports win", () => {
    const root = tmpRoot();
    try {
      const publicDataDir = path.join(root, "public", "data");
      const fallbackDataDir = path.join(root, "deploy-data", "data");
      mkdirSync(publicDataDir, { recursive: true });
      mkdirSync(fallbackDataDir, { recursive: true });
      writeFileSync(path.join(publicDataDir, "meta.json"), '{"source":"local"}');
      writeFileSync(path.join(fallbackDataDir, "meta.json"), '{"source":"fallback"}');

      const result = ensureData({ publicDataDir, fallbackDataDir });

      expect(result).toBe("existing");
      expect(readFileSync(path.join(publicDataDir, "meta.json"), "utf8")).toBe('{"source":"local"}');
      expect(existsSync(path.join(publicDataDir, "meta.json"))).toBe(true);
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
});
