import { describe, expect, it } from "vitest";
import {
  buildLabelComposition,
  buildMapPulse,
  buildMapSpotlights,
  buildSimilarityLinks,
  buildStationMicrostructure,
} from "./mapInsights";
import { lensByKey } from "./lenses";
import type { QuartersDoc, Station } from "../types";

const st = (id: string, over: Partial<Station["metrics"]> = {}): Station => ({
  id,
  name: id,
  ward: "区",
  lines: [],
  lon: 0,
  lat: 0,
  label: "標準",
  metrics: {
    median_ppsm: 800_000,
    tx_count: 20,
    growth_1y: 0.04,
    growth_3y: 0.1,
    growth_5y: 0.2,
    volatility: 0.03,
    dispersion: 0.2,
    liquidity_score: 50,
    relative_value: 0,
    hazard_score: 30,
    pop_resilience: 55,
    redevelopment_score: 60,
    planning_intensity: 50,
    gravity: 50,
    confidence: 2,
    ...over,
  },
});

const quarters: QuartersDoc = {
  schema_version: 1,
  quarters: ["2024Q4", "2025Q4"],
  stations: {
    A: { m: [500_000, 700_000], n: [4, 12] },
    B: { m: [900_000, 1_100_000], n: [0, 3] },
    C: { m: [null, null], n: [0, 0] },
  },
};

describe("buildMapPulse", () => {
  it("summarizes the selected quarter with median price and active station count", () => {
    const pulse = buildMapPulse([st("A"), st("B"), st("C", { median_ppsm: null })], quarters, 1);

    expect(pulse.quarter).toBe("2025Q4");
    expect(pulse.activeStations).toBe(2);
    expect(pulse.medianPpsm).toBe(900_000);
    expect(pulse.totalTransactions).toBe(15);
  });

  it("falls back to snapshot metrics when quarter is latest/null", () => {
    const pulse = buildMapPulse([st("A"), st("B", { median_ppsm: 1_200_000 })], quarters, null);

    expect(pulse.quarter).toBe("2025Q4");
    expect(pulse.medianPpsm).toBe(1_000_000);
    expect(pulse.totalTransactions).toBe(40);
  });
});

describe("buildMapSpotlights", () => {
  it("uses the active lens accessor and omits missing values", () => {
    const out = buildMapSpotlights([
      st("low", { growth_1y: -0.01 }),
      st("top", { growth_1y: 0.13 }),
      st("missing", { growth_1y: null }),
    ], lensByKey("momentum"), 2);

    expect(out.map(x => x.station.id)).toEqual(["top", "low"]);
    expect(out[0].formatted).toContain("+13.0%");
  });
});

describe("buildLabelComposition", () => {
  it("counts labels and returns shares sorted by count", () => {
    const out = buildLabelComposition([
      st("A", { confidence: 2 }),
      { ...st("B"), label: "割安" },
      { ...st("C"), label: "割安" },
    ]);

    expect(out[0]).toMatchObject({ label: "割安", count: 2 });
    expect(out[0].share).toBeCloseTo(2 / 3);
  });
});

describe("buildSimilarityLinks", () => {
  it("creates line features from the selected station to peers with coordinates", () => {
    const selected = st("A");
    const peer = st("B");
    peer.lon = 139.8;
    peer.lat = 35.8;
    const fc = buildSimilarityLinks(selected, {
      schema_version: 1,
      id: "A",
      name: "A",
      series: { quarters: [], median_ppsm: [], tx_count: [] },
      similar: [{ id: "B", name: "B", median_ppsm: 700_000, price_gap: -0.2 }],
      hazard: null,
      redevelopment: null,
      landprice: null,
      hist: null,
    }, [selected, peer]);

    expect(fc.features).toHaveLength(1);
    expect(fc.features[0].geometry.coordinates).toEqual([[0, 0], [139.8, 35.8]]);
    expect(fc.features[0].properties?.gapLabel).toBe("−20.0%");
  });
});

describe("buildStationMicrostructure", () => {
  it("normalizes histogram and peer gaps for compact visualization", () => {
    const micro = buildStationMicrostructure({
      schema_version: 1,
      id: "A",
      name: "A",
      series: { quarters: ["Q1", "Q2"], median_ppsm: [500_000, 700_000], tx_count: [3, 9] },
      similar: [
        { id: "B", name: "B", median_ppsm: 600_000, price_gap: -0.2 },
        { id: "C", name: "C", median_ppsm: 900_000, price_gap: 0.2 },
      ],
      hazard: null,
      redevelopment: null,
      landprice: null,
      hist: { window_quarters: 8, bin_edges: [1, 2, 3], counts: [2, 4] },
    });

    expect(micro.histBars.map(b => b.height)).toEqual([0.5, 1]);
    expect(micro.peerGaps.map(g => g.name)).toEqual(["B", "C"]);
    expect(micro.trend).toBe("up");
  });
});
