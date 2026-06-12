import { create } from "zustand";
import { fetchMeta, fetchQuarters, fetchStations } from "./lib/data";
import type { LensKey } from "./lib/lenses";
import type { MetaDoc, QuartersDoc, StationsDoc } from "./types";

interface AppState {
  lens: LensKey;
  quarterIdx: number | null; // null = latest snapshot
  selectedId: string | null;
  compare: [string | null, string | null];
  status: "loading" | "ready" | "error";
  error: string | null;
  stations: StationsDoc | null;
  quarters: QuartersDoc | null;
  meta: MetaDoc | null;
  setLens: (l: LensKey) => void;
  setQuarter: (i: number | null) => void;
  select: (id: string | null) => void;
  addCompare: (id: string) => void;
  clearCompare: () => void;
  load: () => Promise<void>;
}

let loadStarted = false;

/** Test-only helper: allow load() to run again. */
export function _resetLoad() { loadStarted = false; }

export const useApp = create<AppState>((set, get) => ({
  lens: "price",
  quarterIdx: null,
  selectedId: null,
  compare: [null, null],
  status: "loading",
  error: null,
  stations: null,
  quarters: null,
  meta: null,

  setLens: lens => set({ lens, quarterIdx: lens === "price" ? get().quarterIdx : null }),
  setQuarter: quarterIdx => set({ quarterIdx }),
  select: selectedId => set({ selectedId }),

  addCompare: id => {
    const [a, b] = get().compare;
    if (a === id || b === id) return;
    if (a == null) set({ compare: [id, b] });
    else if (b == null) set({ compare: [a, id] });
    else set({ compare: [b, id] });
  },
  clearCompare: () => set({ compare: [null, null] }),

  load: async () => {
    if (loadStarted) return;
    loadStarted = true;
    try {
      const meta = await fetchMeta();
      const [stations, quarters] = await Promise.all([fetchStations(), fetchQuarters()]);
      set({ meta, stations, quarters, status: "ready" });
    } catch (e) {
      set({ status: "error", error: e instanceof Error ? e.message : String(e) });
    }
  },
}));
