import { describe, expect, it } from "vitest";
import { axesFor, percentileOf, proseFor, AXES } from "./compare";
import type { Station } from "../types";

const st = (name: string, over: Partial<Station["metrics"]> = {}): Station => ({
  id: name, name, ward: "区", lines: [], lon: 0, lat: 0, label: "標準",
  metrics: {
    median_ppsm: 500000, tx_count: 50, growth_1y: 0.02, growth_3y: null, growth_5y: null,
    volatility: 0.03, dispersion: 0.2, liquidity_score: 50, relative_value: 0,
    hazard_score: 30, pop_resilience: 50, gravity: 50, confidence: 2, ...over,
  },
});

describe("percentileOf", () => {
  it("ranks within population", () => {
    expect(percentileOf([1, 2, 3, 4], 4)).toBe(100);
    expect(percentileOf([1, 2, 3, 4], 1)).toBe(0);
    expect(percentileOf([], 1)).toBe(50);
  });
});

describe("axesFor", () => {
  const all = [st("A", { growth_1y: 0.1, hazard_score: 80 }), st("B"), st("C", { growth_1y: -0.05 })];
  it("returns six axes in spec order, 0-100, safety inverted", () => {
    const ax = axesFor(all[0], all);
    expect(ax.map(a => a.key)).toEqual(AXES.map(a => a.key));
    const safety = ax.find(a => a.key === "safety")!;
    expect(safety.value).toBeLessThan(50); // hazard 80 → low safety
    ax.forEach(a => { expect(a.value).toBeGreaterThanOrEqual(0); expect(a.value).toBeLessThanOrEqual(100); });
  });
  it("null metrics fall back to 50 and are flagged", () => {
    const s = st("N", { pop_resilience: null });
    const ax = axesFor(s, [s]);
    const pop = ax.find(a => a.key === "population")!;
    expect(pop.value).toBe(50);
    expect(pop.missing).toBe(true);
  });
});

describe("proseFor", () => {
  it("mentions dimensions with a clear gap, neutrally", () => {
    const a = st("北千住", { growth_1y: 0.12, liquidity_score: 90, hazard_score: 70 });
    const b = st("赤羽", { growth_1y: 0.02, liquidity_score: 60, hazard_score: 20 });
    const text = proseFor(a, b, [a, b]).join("");
    expect(text).toContain("北千住");
    expect(text).toContain("赤羽");
    expect(text).not.toMatch(/勝|負|対決/); // no game language
  });
});
