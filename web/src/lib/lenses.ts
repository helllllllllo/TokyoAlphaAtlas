import { rampColor } from "./color";
import type { StationMetrics } from "../types";

export type LensKey = "price" | "momentum" | "value" | "liquidity" | "risk";

export interface Lens {
  key: LensKey;
  label: string;
  legend: string;
  accessor: (m: StationMetrics) => number | null;
  domain: [number, number];
  ramp: string[]; // low → high
}

export const NULL_COLOR = "#48598a";

export const LENSES: Lens[] = [
  {
    key: "price", label: "価格", legend: "色＝㎡単価",
    accessor: m => m.median_ppsm, domain: [400_000, 2_000_000],
    ramp: ["#3f6fd0", "#9b4fc0", "#d85f7a", "#e0764f"],
  },
  {
    key: "momentum", label: "モメンタム", legend: "色＝1年成長率",
    accessor: m => m.growth_1y, domain: [-0.1, 0.15],
    ramp: ["#3a5fa0", "#5a7ab8", "#c9a86a", "#e0764f"],
  },
  {
    key: "value", label: "割安", legend: "色＝類似駅比の割安度",
    accessor: m => m.relative_value, domain: [-0.25, 0.25],
    ramp: ["#7a4060", "#5a6890", "#4fa080", "#7fe8a8"],
  },
  {
    key: "liquidity", label: "流動性", legend: "色＝取引量の厚さ",
    accessor: m => m.liquidity_score, domain: [0, 100],
    ramp: ["#2a3a60", "#3f6fa0", "#3fa3c4", "#7fd4ef"],
  },
  {
    key: "risk", label: "リスク", legend: "色＝ハザード（赤＝高）",
    accessor: m => m.hazard_score, domain: [0, 100],
    ramp: ["#3f8f6f", "#c9a86a", "#d8745f", "#c43f3f"],
  },
];

export function lensByKey(key: LensKey): Lens {
  const lens = LENSES.find(l => l.key === key);
  if (!lens) throw new Error(`Unknown lens key: "${key}"`);
  return lens;
}

export function colorFor(lens: Lens, value: number | null): string {
  if (value == null) return NULL_COLOR;
  const [lo, hi] = lens.domain;
  return rampColor(lens.ramp, (value - lo) / (hi - lo));
}
