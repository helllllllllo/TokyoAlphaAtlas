import { describe, expect, it } from "vitest";
import { evaluateDeal, percentileFromHist } from "./benchmark";
import type { Hist, Station } from "../types";

const hist: Hist = {
  window_quarters: 8,
  bin_edges: [400000, 500000, 600000, 700000],
  counts: [10, 20, 10],
};

describe("percentileFromHist", () => {
  it("interpolates within bins", () => {
    expect(percentileFromHist(hist, 400000)).toBe(0);
    expect(percentileFromHist(hist, 700000)).toBe(100);
    expect(percentileFromHist(hist, 550000)).toBeCloseTo(50, 0); // 10 + 10 of 40
  });
  it("clamps outside range", () => {
    expect(percentileFromHist(hist, 100)).toBe(0);
    expect(percentileFromHist(hist, 9e9)).toBe(100);
  });
});

describe("evaluateDeal", () => {
  const station: Station = {
    id: "中野", name: "中野", ward: "中野区", lines: [], lon: 0, lat: 0, label: "モメンタム",
    metrics: {
      median_ppsm: 600000, tx_count: 100, growth_1y: 0.09, growth_3y: null, growth_5y: null,
      volatility: 0.03, dispersion: 0.2, liquidity_score: 30, relative_value: 0,
      hazard_score: 62, pop_resilience: 60, gravity: 70, confidence: 2,
    },
  };
  it("computes ppsm, percentile and verdict sentences", () => {
    const r = evaluateDeal({ priceYen: 27500000, sizeM2: 50, rentYenMonthly: 110000 }, station, hist);
    expect(r.ppsm).toBe(550000);
    expect(r.percentile).toBeCloseTo(50, 0);
    expect(r.grossYield).toBeCloseTo(0.048, 3);
    const text = r.verdicts.join("");
    expect(text).toContain("中央値");
    expect(text).toContain("流動性");   // liquidity 30 → thin
    expect(text).toContain("洪水");     // hazard 62 → mentioned
  });
  it("works without hist or rent", () => {
    const r = evaluateDeal({ priceYen: 30000000, sizeM2: 50 }, station, null);
    expect(r.percentile).toBeNull();
    expect(r.grossYield).toBeNull();
    expect(r.verdicts.length).toBeGreaterThan(0);
  });
});
