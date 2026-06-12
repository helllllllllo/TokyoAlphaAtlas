import { describe, expect, it } from "vitest";
import { buildStationFeatures, radiusFor } from "./mapData";
import { lensByKey, NULL_COLOR } from "./lenses";
import type { QuartersDoc, Station } from "../types";

const station = (over: Partial<Station> = {}): Station => ({
  id: "中野", name: "中野", ward: "中野区", lines: ["中央線"], lon: 139.66, lat: 35.7,
  label: "モメンタム",
  metrics: {
    median_ppsm: 660000, tx_count: 100, growth_1y: 0.1, growth_3y: null, growth_5y: null,
    volatility: 0.03, dispersion: 0.2, liquidity_score: 80, relative_value: 0.05,
    hazard_score: 35, pop_resilience: 70, gravity: 75, confidence: 2,
  },
  ...over,
});

const quarters: QuartersDoc = {
  schema_version: 1,
  quarters: ["2023Q3", "2023Q4"],
  stations: { 中野: { m: [500000, 660000], n: [3, 5] } },
};

describe("radiusFor", () => {
  it("grows with sqrt of count and clamps", () => {
    expect(radiusFor(0)).toBe(4);
    expect(radiusFor(400)).toBe(16);
    expect(radiusFor(100)).toBeCloseTo(10, 0);
  });
});

describe("buildStationFeatures", () => {
  it("colors by snapshot metric at latest quarter", () => {
    const fc = buildStationFeatures([station()], quarters, lensByKey("price"), null);
    const p = fc.features[0].properties!;
    expect(p.id).toBe("中野");
    expect(p.color).not.toBe(NULL_COLOR);
    expect(p.opacity).toBeGreaterThan(0.8); // confidence 2
  });
  it("uses quarterly median when scrubbed on price lens", () => {
    const latest = buildStationFeatures([station()], quarters, lensByKey("price"), null);
    const past = buildStationFeatures([station()], quarters, lensByKey("price"), 0);
    expect(past.features[0].properties!.color).not.toBe(latest.features[0].properties!.color);
    expect(past.features[0].properties!.priceLabel).toContain("50.0万");
  });
  it("renders low confidence as hollow gray", () => {
    const s = station({ metrics: { ...station().metrics, confidence: 0, median_ppsm: null } });
    const fc = buildStationFeatures([s], quarters, lensByKey("price"), null);
    const p = fc.features[0].properties!;
    expect(p.opacity).toBeLessThan(0.15);
    expect(p.strokeWidth).toBeGreaterThan(0);
  });
  it("treats a scrubbed station missing from the quarters map as hollow no-data", () => {
    const s = station({ id: "知らない駅", name: "知らない駅" });
    const fc = buildStationFeatures([s], quarters, lensByKey("price"), 0);
    const p = fc.features[0].properties!;
    expect(p.color).toBe(NULL_COLOR); // null median
    expect(p.txLabel).toBe("取引 0件");
    expect(p.opacity).toBeLessThan(0.15); // tx 0 → confidence 0
    expect(p.strokeWidth).toBeGreaterThan(0); // hollow
  });
  it("ignores quarterIdx on non-price lenses", () => {
    const latest = buildStationFeatures([station()], quarters, lensByKey("momentum"), null);
    const scrubbed = buildStationFeatures([station()], quarters, lensByKey("momentum"), 0);
    expect(scrubbed.features[0].properties!.color).toBe(latest.features[0].properties!.color);
  });
});
