import type { Station } from "../types";

export function percentileOf(values: number[], v: number): number {
  if (values.length === 0) return 50;
  if (values.length === 1) return 50;
  const sorted = [...values].sort((a, b) => a - b);
  const below = sorted.filter(x => x < v).length;
  return (100 * below) / (values.length - 1);
}

export interface Axis {
  key: "momentum" | "value" | "liquidity" | "population" | "safety" | "gravity";
  label: string;
}

export const AXES: Axis[] = [
  { key: "momentum", label: "価格の勢い" },
  { key: "value", label: "相対バリュー" },
  { key: "liquidity", label: "流動性" },
  { key: "population", label: "人口基盤" },
  { key: "safety", label: "災害安全" },
  { key: "gravity", label: "駅引力" },
];

export interface AxisValue extends Axis {
  value: number; // 0–100, larger = better
  missing: boolean;
}

export function axesFor(s: Station, all: Station[]): AxisValue[] {
  const pop = (sel: (m: Station["metrics"]) => number | null) =>
    all.map(x => sel(x.metrics)).filter((v): v is number => v != null);

  const pct = (sel: (m: Station["metrics"]) => number | null): { value: number; missing: boolean } => {
    const v = sel(s.metrics);
    if (v == null) return { value: 50, missing: true };
    return { value: percentileOf(pop(sel), v), missing: false };
  };

  const direct = (v: number | null): { value: number; missing: boolean } =>
    v == null ? { value: 50, missing: true } : { value: v, missing: false };

  return [
    { ...AXES[0], ...pct(m => m.growth_1y) },
    { ...AXES[1], ...pct(m => m.relative_value) },
    { ...AXES[2], ...direct(s.metrics.liquidity_score) },
    { ...AXES[3], ...direct(s.metrics.pop_resilience) },
    { ...AXES[4], ...(s.metrics.hazard_score == null ? { value: 50, missing: true } : { value: 100 - s.metrics.hazard_score, missing: false }) },
    { ...AXES[5], ...direct(s.metrics.gravity) },
  ];
}

const GAP = 15; // points of axis difference worth mentioning

/** Neutral per-dimension prose from precomputed axes. No winners, no game language. */
export function proseFor(a: Station, b: Station, ax: AxisValue[], bx: AxisValue[]): string[] {
  const aheadA: string[] = [];
  const aheadB: string[] = [];
  ax.forEach((av, i) => {
    if (av.missing || bx[i].missing) return;
    const d = av.value - bx[i].value;
    if (d >= GAP) aheadA.push(av.label);
    if (d <= -GAP) aheadB.push(av.label);
  });
  const out: string[] = [];
  if (aheadA.length) out.push(`${a.name}は${aheadA.join("・")}で上回る。`);
  if (aheadB.length) out.push(`${b.name}は${aheadB.join("・")}で優位。`);
  if (!out.length) out.push("主要観点に大きな差はない。");
  return out;
}
