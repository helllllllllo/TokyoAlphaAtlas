export const WATCHLIST_KEY = "atlas.watchlist";

const VERSION = 1;
const MAX_WATCHED = 40;

interface WatchBox {
  v: number;
  ids: string[];
}

function normalize(ids: unknown): string[] {
  if (!Array.isArray(ids)) return [];
  const out: string[] = [];
  for (const id of ids) {
    if (typeof id !== "string" || id.length === 0 || out.includes(id)) continue;
    out.push(id);
    if (out.length >= MAX_WATCHED) break;
  }
  return out;
}

function read(): WatchBox {
  try {
    const raw = localStorage.getItem(WATCHLIST_KEY);
    if (!raw) return { v: VERSION, ids: [] };
    const box = JSON.parse(raw) as WatchBox;
    if (box.v !== VERSION) return { v: VERSION, ids: [] };
    return { v: VERSION, ids: normalize(box.ids) };
  } catch {
    return { v: VERSION, ids: [] };
  }
}

function write(ids: string[]): boolean {
  try {
    localStorage.setItem(WATCHLIST_KEY, JSON.stringify({ v: VERSION, ids: normalize(ids) }));
    return true;
  } catch {
    return false;
  }
}

export function listWatchedStations(): string[] {
  return read().ids;
}

export function isWatched(id: string): boolean {
  return read().ids.includes(id);
}

export function toggleWatchedStation(id: string): string[] {
  const current = read().ids;
  const next = current.includes(id)
    ? current.filter(x => x !== id)
    : [id, ...current.filter(x => x !== id)].slice(0, MAX_WATCHED);
  return write(next) ? next : current;
}

export function clearWatchlist(): boolean {
  return write([]);
}
