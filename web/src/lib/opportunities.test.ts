import { describe, expect, it } from "vitest";
import { buildStationThesis, rankOpportunities, scoreOpportunity, type OpportunityProfile } from "./opportunities";
import type { Station } from "../types";

const station = (id: string, over: Partial<Station["metrics"]> = {}): Station => ({
  id,
  name: id,
  ward: "新宿区",
  lines: ["丸ノ内線"],
  lon: 139.7,
  lat: 35.7,
  label: "標準",
  metrics: {
    median_ppsm: 900_000,
    tx_count: 30,
    growth_1y: 0.02,
    growth_3y: 0.08,
    growth_5y: 0.15,
    volatility: 0.04,
    dispersion: 0.18,
    liquidity_score: 55,
    relative_value: 0,
    hazard_score: 35,
    pop_resilience: 55,
    redevelopment_score: 55,
    planning_intensity: 50,
    gravity: 55,
    confidence: 2,
    ...over,
  },
});

describe("scoreOpportunity", () => {
  it("rewards value, momentum, liquidity, population, and gravity while penalizing hazard", () => {
    const strong = station("strong", {
      growth_1y: 0.11,
      liquidity_score: 90,
      relative_value: 0.22,
      hazard_score: 12,
      pop_resilience: 80,
      gravity: 72,
    });
    const risky = station("risky", {
      growth_1y: 0.11,
      liquidity_score: 90,
      relative_value: 0.22,
      hazard_score: 92,
      pop_resilience: 80,
      gravity: 72,
    });

    expect(scoreOpportunity(strong, "balanced").score).toBeGreaterThan(scoreOpportunity(risky, "balanced").score);
    expect(scoreOpportunity(strong, "balanced").drivers.map(d => d.key)).toContain("relative_value");
  });

  it("uses profile weights so momentum and defensive profiles rank different stations first", () => {
    const momentum = station("勢い駅", { growth_1y: 0.16, relative_value: -0.08, hazard_score: 40 });
    const defensive = station("堅実駅", { growth_1y: 0.01, relative_value: 0.05, hazard_score: 5, pop_resilience: 88 });
    const stations = [momentum, defensive];

    expect(rankOpportunities(stations, "momentum")[0].station.id).toBe("勢い駅");
    expect(rankOpportunities(stations, "defensive")[0].station.id).toBe("堅実駅");
  });

  it("keeps thin-data stations visible but lowers confidence", () => {
    const thin = station("thin", { confidence: 0, tx_count: 2, liquidity_score: 5 });

    const result = scoreOpportunity(thin, "balanced");

    expect(result.score).toBeLessThan(45);
    expect(result.warnings).toContain("データ薄");
  });
});

describe("rankOpportunities", () => {
  it("sorts descending and limits results", () => {
    const out = rankOpportunities([
      station("A", { relative_value: -0.2, growth_1y: -0.04 }),
      station("B", { relative_value: 0.2, growth_1y: 0.08 }),
      station("C", { relative_value: 0.1, growth_1y: 0.02 }),
    ], "balanced", 2);

    expect(out.map(x => x.station.id)).toEqual(["B", "C"]);
  });

  it("rejects unknown profiles at compile time via the OpportunityProfile union", () => {
    const profile: OpportunityProfile = "value";
    expect(rankOpportunities([station("A")], profile)).toHaveLength(1);
  });
});

describe("buildStationThesis", () => {
  it("turns metrics into concise analyst notes without winner language", () => {
    const notes = buildStationThesis(station("中野", {
      growth_1y: 0.13,
      liquidity_score: 88,
      relative_value: 0.18,
      hazard_score: 72,
      pop_resilience: 30,
    }));

    expect(notes[0]).toContain("中野");
    expect(notes.join("")).toContain("割安");
    expect(notes.join("")).toContain("ハザード");
    expect(notes.join("")).not.toMatch(/勝|負|対決|おすすめ/);
  });
});
