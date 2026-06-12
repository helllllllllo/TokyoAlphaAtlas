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
  opacity: number;
  strokeWidth: number;
  strokeColor: string;
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
): GeoJSON.FeatureCollection<GeoJSON.Point, StationFeatureProps> {
  const features = stations.map(s => {
    const q = quarters.stations[s.id];
    const scrubbed = quarterIdx != null && lens.key === "price";
    const median = scrubbed ? (q?.m[quarterIdx] ?? null) : s.metrics.median_ppsm;
    const tx = scrubbed ? (q?.n[quarterIdx] ?? 0) : s.metrics.tx_count;
    const value = scrubbed ? median : lens.accessor(s.metrics);
    const conf = scrubbed ? (tx >= 10 ? 2 : tx >= 3 ? 1 : 0) : s.metrics.confidence;

    const opacity = conf === 2 ? 0.9 : conf === 1 ? 0.55 : 0.08;
    const priceLabel = `㎡単価 ${formatMan(median)}円`;
    return {
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [s.lon, s.lat] },
      properties: {
        id: s.id,
        name: s.name,
        color: colorFor(lens, value),
        radius: radiusFor(tx),
        opacity,
        strokeWidth: conf === 0 ? 1.5 : 0,
        strokeColor: "#48598a",
        labelText: `${s.name} ${formatMan(median)}`,
        priceLabel,
        growthLabel: `1年成長 ${formatPct(s.metrics.growth_1y)}`,
        txLabel: `取引 ${tx}件`,
      },
    };
  });
  return { type: "FeatureCollection", features };
}
