import { beforeEach, describe, expect, it, vi } from "vitest";
import { listDeals, saveDeal, removeDeal, DEALS_KEY } from "./deals";

beforeEach(() => localStorage.clear());

describe("deals storage", () => {
  it("saves and lists", () => {
    saveDeal({ stationId: "中野", priceYen: 30000000, sizeM2: 50, builtYear: 2005 });
    const all = listDeals();
    expect(all).toHaveLength(1);
    expect(all[0].stationId).toBe("中野");
    expect(all[0].id).toBeTruthy();
  });
  it("removes by id", () => {
    saveDeal({ stationId: "中野", priceYen: 1, sizeM2: 1 });
    const id = listDeals()[0].id;
    removeDeal(id);
    expect(listDeals()).toHaveLength(0);
  });
  it("ignores corrupt or wrong-version storage", () => {
    localStorage.setItem(DEALS_KEY, "not json");
    expect(listDeals()).toEqual([]);
    localStorage.setItem(DEALS_KEY, JSON.stringify({ v: 99, deals: [{}] }));
    expect(listDeals()).toEqual([]);
  });
  it("returns null when storage write fails (quota)", () => {
    const spy = vi.spyOn(localStorage, "setItem").mockImplementation(() => {
      throw new DOMException("QuotaExceededError");
    });
    try {
      const deal = saveDeal({ stationId: "中野", priceYen: 1, sizeM2: 1 });
      expect(deal).toBeNull();
      expect(removeDeal("whatever")).toBe(false);
    } finally {
      spy.mockRestore();
    }
  });
});
