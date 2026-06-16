import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  WATCHLIST_KEY,
  clearWatchlist,
  isWatched,
  listWatchedStations,
  toggleWatchedStation,
} from "./watchlist";

beforeEach(() => localStorage.clear());

describe("watchlist storage", () => {
  it("toggles station ids and keeps newest first", () => {
    expect(toggleWatchedStation("中野")).toEqual(["中野"]);
    expect(toggleWatchedStation("三軒茶屋")).toEqual(["三軒茶屋", "中野"]);
    expect(isWatched("中野")).toBe(true);
    expect(toggleWatchedStation("中野")).toEqual(["三軒茶屋"]);
  });

  it("deduplicates and caps the watchlist", () => {
    for (let i = 0; i < 45; i++) toggleWatchedStation(`S${i}`);

    const ids = listWatchedStations();

    expect(ids).toHaveLength(40);
    expect(ids[0]).toBe("S44");
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("falls back to empty when storage is corrupt or the version is unknown", () => {
    localStorage.setItem(WATCHLIST_KEY, "not-json");
    expect(listWatchedStations()).toEqual([]);

    localStorage.setItem(WATCHLIST_KEY, JSON.stringify({ v: 99, ids: ["A"] }));
    expect(listWatchedStations()).toEqual([]);
  });

  it("reports failure when storage cannot be written", () => {
    const spy = vi.spyOn(localStorage, "setItem").mockImplementation(() => {
      throw new DOMException("QuotaExceededError");
    });
    try {
      expect(toggleWatchedStation("A")).toEqual([]);
      expect(clearWatchlist()).toBe(false);
    } finally {
      spy.mockRestore();
    }
  });
});
