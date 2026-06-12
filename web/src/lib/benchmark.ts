import { formatMan, formatPct } from "./format";
import type { Hist, Station } from "../types";

export function percentileFromHist(hist: Hist, ppsm: number): number {
  const { bin_edges: e, counts } = hist;
  const total = counts.reduce((a, b) => a + b, 0);
  if (total === 0) return 50;
  if (ppsm <= e[0]) return 0;
  if (ppsm >= e[e.length - 1]) return 100;
  let below = 0;
  for (let i = 0; i < counts.length; i++) {
    if (ppsm >= e[i + 1]) {
      below += counts[i];
    } else {
      below += counts[i] * ((ppsm - e[i]) / (e[i + 1] - e[i]));
      break;
    }
  }
  return (100 * below) / total;
}

export interface DealInput {
  priceYen: number;
  sizeM2: number;
  builtYear?: number;
  rentYenMonthly?: number;
}

export interface DealResult {
  ppsm: number;
  percentile: number | null;
  grossYield: number | null;
  verdicts: string[];
}

export function evaluateDeal(deal: DealInput, station: Station, hist: Hist | null): DealResult {
  const ppsm = deal.priceYen / deal.sizeM2;
  const m = station.metrics;
  const percentile = hist ? percentileFromHist(hist, ppsm) : null;
  const grossYield = deal.rentYenMonthly ? (deal.rentYenMonthly * 12) / deal.priceYen : null;

  const verdicts: string[] = [];
  if (m.median_ppsm != null) {
    const gap = ppsm / m.median_ppsm - 1;
    const dir = gap < -0.02 ? "下回る" : gap > 0.02 ? "上回る" : "ほぼ一致する";
    verdicts.push(
      `この物件の㎡単価は${formatMan(ppsm)}円。${station.name}の直近中央値（${formatMan(m.median_ppsm)}円）を${formatPct(Math.abs(gap))}${dir}。` +
      (percentile != null ? `直近2年の取引分布では下から${percentile.toFixed(0)}%の位置。` : ""),
    );
  }
  verdicts.push(
    m.liquidity_score >= 60
      ? `流動性は厚い（駅間percentile ${m.liquidity_score.toFixed(0)}）。出口は取りやすい部類。`
      : `流動性は薄い（駅間percentile ${m.liquidity_score.toFixed(0)}）。出口に時間がかかる可能性。`,
  );
  if (m.hazard_score != null) {
    verdicts.push(
      m.hazard_score > 50
        ? `洪水等のハザード負担が高め（スコア${m.hazard_score.toFixed(0)}）。保険・長期保有リスクを織り込むこと。`
        : `ハザード負担は低め（スコア${m.hazard_score.toFixed(0)}）。`,
    );
  }
  if (m.growth_1y != null) {
    verdicts.push(
      m.growth_1y > 0.03
        ? `エリアの価格モメンタムはプラス（1年${formatPct(m.growth_1y)}）。`
        : `エリアの価格モメンタムは弱い（1年${formatPct(m.growth_1y)}）。`,
    );
  }
  if (grossYield != null) {
    verdicts.push(`表面利回り ${formatPct(grossYield)}（参考値・家賃相場データなし）。`);
  }
  return { ppsm, percentile, grossYield, verdicts };
}
