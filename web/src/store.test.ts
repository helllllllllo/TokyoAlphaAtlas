import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { _resetLoad, useApp } from "./store";

beforeEach(() => {
  _resetLoad();
  useApp.setState({
    lens: "price", quarterIdx: null, selectedId: null, compare: [null, null],
    status: "loading", error: null, stations: null, quarters: null, meta: null,
  });
});

afterEach(() => vi.unstubAllGlobals());

describe("store", () => {
  it("switching lens away from price resets the quarter scrub", () => {
    useApp.getState().setQuarter(10);
    useApp.getState().setLens("momentum");
    expect(useApp.getState().quarterIdx).toBeNull();
  });
  it("addCompare fills slots then rotates", () => {
    const s = useApp.getState();
    s.addCompare("A");
    s.addCompare("B");
    s.addCompare("C");
    expect(useApp.getState().compare).toEqual(["B", "C"]);
  });
  it("addCompare ignores duplicates", () => {
    useApp.getState().addCompare("A");
    useApp.getState().addCompare("A");
    expect(useApp.getState().compare).toEqual(["A", null]);
  });
});

describe("store load", () => {
  it("loads once even when called twice concurrently", async () => {
    const docs: Record<string, unknown> = {
      "meta.json": { schema_version: 1, asof: "2023Q4", generated_rows: {}, sources: {} },
      "stations.json": { schema_version: 1, asof: "2023Q4", stations: [] },
      "quarters.json": { schema_version: 1, quarters: [], stations: {} },
    };
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      const key = Object.keys(docs).find(k => url.endsWith(k));
      if (!key) return new Response("not found", { status: 404 });
      return new Response(JSON.stringify(docs[key]), { status: 200 });
    }));

    await Promise.all([useApp.getState().load(), useApp.getState().load()]);

    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(3);
    expect(useApp.getState().status).toBe("ready");
    expect(useApp.getState().meta?.asof).toBe("2023Q4");
  });

  it("sets error status with a message when fetch fails", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));

    await useApp.getState().load();

    expect(useApp.getState().status).toBe("error");
    expect(useApp.getState().error).toBeTruthy();
  });
});
