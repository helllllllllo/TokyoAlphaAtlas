import { describe, expect, it } from "vitest";
import { matchStations } from "./SearchBox";
import type { Station } from "../types";

const st = (name: string, ward = "中野区"): Station => ({
  id: name, name, ward, lines: [], lon: 0, lat: 0, label: "標準",
  metrics: {
    median_ppsm: 1, tx_count: 1, growth_1y: null, growth_3y: null, growth_5y: null,
    volatility: null, dispersion: null, liquidity_score: 0, relative_value: null,
    hazard_score: null, pop_resilience: null, redevelopment_score: null,
    planning_intensity: null, gravity: 0, confidence: 1,
  },
});

describe("matchStations", () => {
  const all = [st("中野"), st("中野坂上"), st("東中野"), st("新宿", "新宿区")];
  it("prefix matches rank before substring matches", () => {
    const r = matchStations(all, "中野").map(s => s.name);
    expect(r[0]).toBe("中野");
    expect(r).toContain("東中野");
  });
  it("matches ward names too", () => {
    expect(matchStations(all, "新宿区").map(s => s.name)).toEqual(["新宿"]);
  });
  it("empty query returns nothing", () => {
    expect(matchStations(all, "")).toEqual([]);
  });
});
