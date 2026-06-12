import { afterEach, describe, expect, it, vi } from "vitest";
import { SchemaMismatchError, fetchDetail, fetchJson, fetchMeta } from "./data";

function mockFetch(map: Record<string, unknown>) {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    for (const [k, v] of Object.entries(map)) {
      if (url.endsWith(k)) {
        if (v === 404) return new Response("not found", { status: 404 });
        return new Response(JSON.stringify(v), { status: 200 });
      }
    }
    return new Response("not found", { status: 404 });
  }));
}

afterEach(() => vi.unstubAllGlobals());

describe("fetchJson", () => {
  it("throws on http error", async () => {
    mockFetch({});
    await expect(fetchJson("/data/nope.json")).rejects.toThrow(/404/);
  });
});

describe("fetchMeta", () => {
  it("accepts matching schema version", async () => {
    mockFetch({ "meta.json": { schema_version: 1, asof: "2023Q4", generated_rows: {}, sources: {} } });
    const meta = await fetchMeta();
    expect(meta.asof).toBe("2023Q4");
  });
  it("rejects mismatched schema version", async () => {
    mockFetch({ "meta.json": { schema_version: 99, asof: "2023Q4", generated_rows: {}, sources: {} } });
    await expect(fetchMeta()).rejects.toBeInstanceOf(SchemaMismatchError);
  });
});

describe("fetchDetail", () => {
  it("returns null on 404 and caches results", async () => {
    mockFetch({ "station/中野.json": { id: "中野" }, "station/無い.json": 404 });
    expect(await fetchDetail("無い")).toBeNull();
    const d1 = await fetchDetail("中野");
    const d2 = await fetchDetail("中野");
    expect(d1).toBe(d2); // same object → cached
    expect(vi.mocked(fetch).mock.calls.filter(c => String(c[0]).includes("中野")).length).toBe(1);
  });
});
