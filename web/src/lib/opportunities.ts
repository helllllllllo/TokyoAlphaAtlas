import type { Station } from "../types";

export type OpportunityProfile = "balanced" | "value" | "momentum" | "defensive";

export interface OpportunityDriver {
  key: "relative_value" | "momentum" | "liquidity" | "safety" | "population" | "gravity";
  label: string;
  value: number;
}

export interface OpportunityScore {
  station: Station;
  profile: OpportunityProfile;
  score: number;
  drivers: OpportunityDriver[];
  warnings: string[];
}

const DRIVER_LABELS: Record<OpportunityDriver["key"], string> = {
  relative_value: "類似駅比の割安度",
  momentum: "1年成長",
  liquidity: "流動性",
  safety: "災害安全",
  population: "人口基盤",
  gravity: "駅引力",
};

const WEIGHTS: Record<OpportunityProfile, Record<OpportunityDriver["key"], number>> = {
  balanced: {
    relative_value: 0.25,
    momentum: 0.22,
    liquidity: 0.18,
    safety: 0.14,
    population: 0.11,
    gravity: 0.10,
  },
  value: {
    relative_value: 0.42,
    liquidity: 0.19,
    safety: 0.16,
    momentum: 0.11,
    population: 0.07,
    gravity: 0.05,
  },
  momentum: {
    momentum: 0.45,
    liquidity: 0.18,
    relative_value: 0.15,
    gravity: 0.10,
    population: 0.07,
    safety: 0.05,
  },
  defensive: {
    safety: 0.34,
    population: 0.23,
    relative_value: 0.19,
    liquidity: 0.14,
    momentum: 0.06,
    gravity: 0.04,
  },
};

function clamp01(x: number): number {
  if (!Number.isFinite(x)) return 0.5;
  return Math.max(0, Math.min(1, x));
}

function scale(value: number | null, min: number, max: number, fallback = 0.5): number {
  if (value == null || !Number.isFinite(value)) return fallback * 100;
  return clamp01((value - min) / (max - min)) * 100;
}

function direct(value: number | null, fallback = 50): number {
  if (value == null || !Number.isFinite(value)) return fallback;
  return Math.max(0, Math.min(100, value));
}

function components(station: Station): Record<OpportunityDriver["key"], number> {
  const m = station.metrics;
  return {
    relative_value: scale(m.relative_value, -0.20, 0.25),
    momentum: scale(m.growth_1y, -0.08, 0.16),
    liquidity: direct(m.liquidity_score),
    safety: m.hazard_score == null ? 50 : 100 - direct(m.hazard_score),
    population: direct(m.pop_resilience),
    gravity: direct(m.gravity),
  };
}

function confidencePenalty(station: Station): number {
  if (station.metrics.confidence === 0) return 24;
  if (station.metrics.confidence === 1) return 7;
  return 0;
}

export function scoreOpportunity(station: Station, profile: OpportunityProfile = "balanced"): OpportunityScore {
  const values = components(station);
  const weights = WEIGHTS[profile];
  const raw = (Object.keys(weights) as OpportunityDriver["key"][])
    .reduce((sum, key) => sum + values[key] * weights[key], 0);
  const score = Math.round(Math.max(0, Math.min(100, raw - confidencePenalty(station))));

  const drivers = (Object.keys(values) as OpportunityDriver["key"][])
    .map(key => ({ key, label: DRIVER_LABELS[key], value: Math.round(values[key]) }))
    .sort((a, b) => (b.value * weights[b.key]) - (a.value * weights[a.key]))
    .slice(0, 3);

  const warnings: string[] = [];
  if (station.metrics.confidence === 0 || station.metrics.tx_count < 10) warnings.push("データ薄");
  if (station.metrics.hazard_score != null && station.metrics.hazard_score >= 65) warnings.push("ハザード高");
  if (station.metrics.pop_resilience != null && station.metrics.pop_resilience <= 35) warnings.push("人口基盤弱め");

  return { station, profile, score, drivers, warnings };
}

export function rankOpportunities(
  stations: Station[],
  profile: OpportunityProfile = "balanced",
  limit = 12,
): OpportunityScore[] {
  return stations
    .map(station => scoreOpportunity(station, profile))
    .sort((a, b) => b.score - a.score || b.station.metrics.tx_count - a.station.metrics.tx_count)
    .slice(0, limit);
}

export function buildStationThesis(station: Station): string[] {
  const m = station.metrics;
  const notes: string[] = [];
  const positives: string[] = [];

  if (m.relative_value != null && m.relative_value >= 0.12) positives.push("類似駅比で割安");
  if (m.growth_1y != null && m.growth_1y >= 0.08) positives.push("足元の価格成長が強い");
  if (m.liquidity_score >= 70) positives.push("取引量が厚い");
  if (m.pop_resilience != null && m.pop_resilience >= 70) positives.push("人口基盤が強い");
  if (m.gravity >= 70) positives.push("駅引力が高い");

  if (positives.length > 0) {
    notes.push(`${station.name}は${positives.slice(0, 3).join("・")}ため、追加調査の入口になりやすい。`);
  } else {
    notes.push(`${station.name}は主要指標が中庸で、価格・流動性・リスクを並べて確認したい駅。`);
  }

  const cautions: string[] = [];
  if (m.hazard_score != null && m.hazard_score >= 65) cautions.push(`ハザードスコア${m.hazard_score.toFixed(0)}は重め`);
  if (m.confidence <= 1 || m.tx_count < 10) cautions.push("直近取引が薄くブレやすい");
  if (m.pop_resilience != null && m.pop_resilience <= 35) cautions.push("人口レジリエンスは低め");
  if (m.volatility != null && m.volatility >= 0.08) cautions.push("四半期変動が大きい");

  if (cautions.length > 0) {
    notes.push(`注意点: ${cautions.join("・")}。`);
  }

  return notes;
}
