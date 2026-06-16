import { colorFor, type Lens } from "./lenses";
import { formatMan, formatPct } from "./format";
import type { QuartersDoc, Station } from "../types";

export function radiusFor(txCount: number): number {
  return 4 + 12 * Math.sqrt(Math.min(txCount, 400) / 400);
}

export interface StationFeatureProps {
  id: string;
  name: string;
  color: string;
  radius: number;
  haloRadius: number;
  glowOpacity: number;
  volatilityWidth: number;
  volatilityOpacity: number;
  opacity: number;
  strokeWidth: number;
  strokeColor: string;
  selected: boolean;
  labelText: string;
  priceLabel: string;
  growthLabel: string;
  txLabel: string;
}

export function buildStationFeatures(
  stations: Station[],
  quarters: QuartersDoc,
  lens: Lens,
  quarterIdx: number | null,
  selectedId: string | null = null,
): GeoJSON.FeatureCollection<GeoJSON.Point, StationFeatureProps> {
  const features = stations.map(s => {
    const q = quarters.stations[s.id];
    const scrubbed = quarterIdx != null && lens.key === "price";
    const median = scrubbed ? (q?.m[quarterIdx] ?? null) : s.metrics.median_ppsm;
    const tx = scrubbed ? (q?.n[quarterIdx] ?? 0) : s.metrics.tx_count;
    const value = scrubbed ? median : lens.accessor(s.metrics);
    // thresholds mirror pipeline config MIN_WINDOW_TX=10 / MIN_QUARTER_TX=3 (pipeline/atlas/config.py) — keep in sync
    const conf = scrubbed ? (tx >= 10 ? 2 : tx >= 3 ? 1 : 0) : s.metrics.confidence;

    const opacity = conf === 2 ? 0.9 : conf === 1 ? 0.55 : 0.08;
    const radius = radiusFor(tx);
    const volatility = s.metrics.volatility;
    const volT = volatility == null ? 0 : Math.max(0, Math.min(1, (volatility - 0.08) / 0.28));
    const volatilityOpacity = conf === 0 || volatility == null ? 0 : 0.12 + 0.46 * volT;
    const priceLabel = `㎡単価 ${formatMan(median)}円`;
    return {
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [s.lon, s.lat] },
      properties: {
        id: s.id,
        name: s.name,
        color: colorFor(lens, value),
        radius,
        haloRadius: radius + (conf === 2 ? 9 : conf === 1 ? 6 : 3),
        glowOpacity: conf === 2 ? 0.26 : conf === 1 ? 0.14 : 0.04,
        volatilityWidth: conf === 0 || volatility == null ? 0 : 0.8 + 3.2 * volT,
        volatilityOpacity,
        opacity,
        strokeWidth: conf === 0 ? 1.5 : 0.7,
        strokeColor: conf === 0 ? "#48598a" : "#08101e",
        selected: s.id === selectedId,
        labelText: `${s.name} ${formatMan(median)}`,
        priceLabel,
        // snapshot growth_1y, not historical — flag it when scrubbed
        growthLabel: `1年成長 ${formatPct(s.metrics.growth_1y)}${scrubbed ? "（現時点）" : ""}`,
        txLabel: `取引 ${tx}件`,
      },
    };
  });
  return { type: "FeatureCollection", features };
}
