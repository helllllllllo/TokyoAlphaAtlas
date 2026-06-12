import { describe, expect, it } from "vitest";
import { lerpColor } from "./color";
import { LENSES, colorFor, lensByKey } from "./lenses";
import type { StationMetrics } from "../types";

const M: StationMetrics = {
  median_ppsm: 800000, tx_count: 100, growth_1y: 0.09, growth_3y: 0.2,
  growth_5y: 0.35, volatility: 0.03, dispersion: 0.2, liquidity_score: 80,
  relative_value: 0.12, hazard_score: 60, pop_resilience: 70, gravity: 75, confidence: 2,
};

describe("lerpColor", () => {
  it("interpolates hex", () => {
    expect(lerpColor("#000000", "#ffffff", 0.5)).toBe("#808080");
    expect(lerpColor("#ff0000", "#00ff00", 0)).toBe("#ff0000");
  });
  it("throws on malformed hex in dev", () => {
    expect(() => lerpColor("#zzzzzz", "#ffffff", 0.5)).toThrow(/malformed hex/);
    expect(() => lerpColor("#000000", "not-a-color", 0.5)).toThrow(/malformed hex/);
  });
});

describe("lenses", () => {
  it("has the five spec lenses in order", () => {
    expect(LENSES.map(l => l.key)).toEqual(["price", "momentum", "value", "liquidity", "risk"]);
    expect(lensByKey("price").label).toBe("価格");
  });
  it("accessors read the right metric", () => {
    expect(lensByKey("price").accessor(M)).toBe(800000);
    expect(lensByKey("momentum").accessor(M)).toBe(0.09);
    expect(lensByKey("risk").accessor(M)).toBe(60);
  });
  it("colorFor clamps to domain and returns gray for null", () => {
    const lens = lensByKey("price");
    expect(colorFor(lens, null)).toBe("#48598a");
    expect(colorFor(lens, -1)).toBe(colorFor(lens, lens.domain[0]));
    expect(colorFor(lens, 99e9)).toBe(colorFor(lens, lens.domain[1]));
  });
});
