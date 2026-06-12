export const DEALS_KEY = "atlas.deals";
const VERSION = 1;

export interface SavedDeal {
  id: string;
  stationId: string;
  priceYen: number;
  sizeM2: number;
  builtYear?: number;
  rentYenMonthly?: number;
  savedAt: string;
}

interface Box { v: number; deals: SavedDeal[]; }

function read(): Box {
  try {
    const raw = localStorage.getItem(DEALS_KEY);
    if (!raw) return { v: VERSION, deals: [] };
    const box = JSON.parse(raw) as Box;
    if (box.v !== VERSION || !Array.isArray(box.deals)) return { v: VERSION, deals: [] };
    return box;
  } catch {
    return { v: VERSION, deals: [] };
  }
}

export function listDeals(): SavedDeal[] {
  return read().deals;
}

export function saveDeal(d: Omit<SavedDeal, "id" | "savedAt">): SavedDeal {
  const box = read();
  const deal: SavedDeal = {
    ...d,
    id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    savedAt: new Date().toISOString(),
  };
  box.deals.push(deal);
  localStorage.setItem(DEALS_KEY, JSON.stringify(box));
  return deal;
}

export function removeDeal(id: string): void {
  const box = read();
  box.deals = box.deals.filter(d => d.id !== id);
  localStorage.setItem(DEALS_KEY, JSON.stringify(box));
}
