import { DATA_BASE, SUPPORTED_SCHEMA_VERSION } from "../config";
import type { MetaDoc, QuartersDoc, StationDetail, StationsDoc } from "../types";

export class SchemaMismatchError extends Error {
  constructor(got: number) {
    super(`データのスキーマバージョン (${got}) がアプリ (${SUPPORTED_SCHEMA_VERSION}) と一致しません。`);
  }
}

export async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return (await res.json()) as T;
}

export async function fetchMeta(): Promise<MetaDoc> {
  const meta = await fetchJson<MetaDoc>(`${DATA_BASE}/meta.json`);
  if (meta.schema_version !== SUPPORTED_SCHEMA_VERSION) {
    throw new SchemaMismatchError(meta.schema_version);
  }
  return meta;
}

export const fetchStations = () => fetchJson<StationsDoc>(`${DATA_BASE}/stations.json`);
export const fetchQuarters = () => fetchJson<QuartersDoc>(`${DATA_BASE}/quarters.json`);

const detailCache = new Map<string, StationDetail | null>();

export async function fetchDetail(id: string): Promise<StationDetail | null> {
  if (detailCache.has(id)) return detailCache.get(id)!;
  const res = await fetch(`${DATA_BASE}/station/${id}.json`);
  const detail = res.ok ? ((await res.json()) as StationDetail) : null;
  detailCache.set(id, detail);
  return detail;
}
