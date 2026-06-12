export interface StationMetrics {
  median_ppsm: number | null;
  tx_count: number;
  growth_1y: number | null;
  growth_3y: number | null;
  growth_5y: number | null;
  volatility: number | null;
  dispersion: number | null;
  liquidity_score: number;
  relative_value: number | null;
  hazard_score: number | null;
  pop_resilience: number | null;
  gravity: number;
  confidence: 0 | 1 | 2;
}

export interface Station {
  id: string;
  name: string;
  ward: string;
  lines: string[];
  lon: number;
  lat: number;
  label: string;
  metrics: StationMetrics;
}

export interface StationsDoc {
  schema_version: number;
  asof: string;
  stations: Station[];
}

export interface QuartersDoc {
  schema_version: number;
  quarters: string[];
  stations: Record<string, { m: (number | null)[]; n: number[] }>;
}

export interface SimilarStation {
  id: string;
  name: string;
  median_ppsm: number | null;
  price_gap: number | null;
}

export interface Hist {
  window_quarters: number;
  bin_edges: number[];
  counts: number[];
}

export interface StationDetail {
  schema_version: number;
  id: string;
  name: string;
  series: { quarters: string[]; median_ppsm: (number | null)[]; tx_count: number[] };
  similar: SimilarStation[];
  hazard: { flood: number | null; landslide: boolean | null; liquefaction: number | null } | null;
  landprice: { years: number[]; price: number[] } | null;
  hist: Hist | null;
}

export interface MetaDoc {
  schema_version: number;
  asof: string;
  generated_rows: Record<string, number | string>;
  sources: Record<string, unknown>;
}
