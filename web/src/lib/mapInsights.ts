import { formatMan, formatPct } from "./format";
import type { Lens } from "./lenses";
import type { QuartersDoc, Station, StationDetail } from "../types";

export interface MapPulse {
  quarter: string;
  activeStations: number;
  medianPpsm: number | null;
  totalTransactions: number;
}

export interface MapSpotlight {
  station: Station;
  formatted: string;
}

export interface LabelComposition {
  label: string;
  count: number;
  share: number;
}

export interface SimilarityLinkProps {
  from: string;
  to: string;
  toName: string;
  gap: number | null;
  gapLabel: string;
  color: string;
  width: number;
}

export interface StationMicrostructure {
  histBars: { height: number; count: number }[];
  peerGaps: { name: string; value: number; width: number; tone: "cheap" | "expensive" }[];
  trend: "up" | "down" | "flat" | "unknown";
}

function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1
    ? sorted[mid]
    : (sorted[mid - 1] + sorted[mid]) / 2;
}

export function buildMapPulse(
  stations: Station[],
  quarters: QuartersDoc,
  quarterIdx: number | null,
): MapPulse {
  const idx = quarterIdx ?? Math.max(quarters.quarters.length - 1, 0);
  const values: number[] = [];
  let activeStations = 0;
  let totalTransactions = 0;

  for (const station of stations) {
    const q = quarters.stations[station.id];
    const price = quarterIdx == null
      ? station.metrics.median_ppsm
      : q?.m[idx] ?? null;
    const tx = quarterIdx == null
      ? station.metrics.tx_count
      : q?.n[idx] ?? 0;
    if (price != null && Number.isFinite(price)) values.push(price);
    if (tx > 0) activeStations += 1;
    totalTransactions += tx;
  }

  return {
    quarter: quarters.quarters[idx] ?? "—",
    activeStations,
    medianPpsm: median(values),
    totalTransactions,
  };
}

function formatLensValue(lens: Lens, value: number): string {
  if (lens.key === "price") return `${formatMan(value)}円/㎡`;
  if (lens.key === "momentum" || lens.key === "value") return formatPct(value);
  return `${Math.round(value)}`;
}

export function buildMapSpotlights(
  stations: Station[],
  lens: Lens,
  limit = 5,
): MapSpotlight[] {
  return stations
    .map(station => ({ station, value: lens.accessor(station.metrics) }))
    .filter((item): item is { station: Station; value: number } => item.value != null && Number.isFinite(item.value))
    .sort((a, b) => b.value - a.value || b.station.metrics.tx_count - a.station.metrics.tx_count)
    .slice(0, limit)
    .map(({ station, value }) => ({ station, formatted: formatLensValue(lens, value) }));
}

export function buildLabelComposition(stations: Station[]): LabelComposition[] {
  const counts = new Map<string, number>();
  for (const station of stations) {
    counts.set(station.label, (counts.get(station.label) ?? 0) + 1);
  }
  const total = Math.max(stations.length, 1);
  return [...counts.entries()]
    .map(([label, count]) => ({ label, count, share: count / total }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label, "ja"));
}

export function buildSimilarityLinks(
  selected: Station,
  detail: StationDetail | null,
  stations: Station[],
): GeoJSON.FeatureCollection<GeoJSON.LineString, SimilarityLinkProps> {
  if (!detail?.similar.length) return { type: "FeatureCollection", features: [] };
  const byId = new Map(stations.map(station => [station.id, station]));
  const features = detail.similar.flatMap(peer => {
    const target = byId.get(peer.id);
    if (!target) return [];
    const gap = peer.price_gap;
    const cheap = gap != null && gap < 0;
    return [{
      type: "Feature" as const,
      geometry: {
        type: "LineString" as const,
        coordinates: [[selected.lon, selected.lat], [target.lon, target.lat]],
      },
      properties: {
        from: selected.id,
        to: target.id,
        toName: target.name,
        gap,
        gapLabel: formatPct(gap),
        color: cheap ? "#7fe8a8" : "#c9a86a",
        width: gap == null ? 1.2 : 1.2 + Math.min(Math.abs(gap), 0.6) * 4,
      },
    }];
  });
  return { type: "FeatureCollection", features };
}

export function buildStationMicrostructure(detail: StationDetail): StationMicrostructure {
  const maxCount = Math.max(...(detail.hist?.counts ?? [0]), 1);
  const histBars = (detail.hist?.counts ?? []).map(count => ({
    count,
    height: count / maxCount,
  }));

  const peerGaps = detail.similar
    .filter(peer => peer.price_gap != null)
    .slice(0, 6)
    .map(peer => {
      const value = peer.price_gap ?? 0;
      return {
        name: peer.name,
        value,
        width: Math.min(Math.abs(value), 0.75) / 0.75,
        tone: value < 0 ? "cheap" as const : "expensive" as const,
      };
    });

  const vals = detail.series.median_ppsm.filter((v): v is number => v != null);
  const first = vals.at(-5) ?? vals[0];
  const last = vals.at(-1);
  const delta = first != null && last != null && first > 0 ? (last - first) / first : null;
  const trend = delta == null ? "unknown" : delta > 0.04 ? "up" : delta < -0.04 ? "down" : "flat";

  return { histBars, peerGaps, trend };
}
