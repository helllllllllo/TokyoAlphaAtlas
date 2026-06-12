export function formatMan(yen: number | null): string {
  if (yen == null) return "—";
  return `${(yen / 10000).toFixed(1)}万`;
}

export function formatPct(x: number | null): string {
  if (x == null) return "—";
  const v = Math.abs(x * 100).toFixed(1);
  if (x > 0) return `+${v}%`;
  if (x < 0) return `−${v}%`;
  return `${v}%`;
}

export function formatYen(yen: number | null): string {
  if (yen == null) return "—";
  return `${Math.round(yen / 10000).toLocaleString("ja-JP")}万円`;
}
