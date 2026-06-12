import { useMemo, useState } from "react";
import {
  PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer,
} from "recharts";
import { matchStations } from "../components/SearchBox";
import { axesFor, proseFor, AXES } from "../lib/compare";
import { formatMan, formatPct } from "../lib/format";
import { useApp } from "../store";
import type { Station } from "../types";

function StationPicker({ slot, value }: { slot: 0 | 1; value: Station | null }) {
  const { stations, compare } = useApp();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const hits = useMemo(() => matchStations(stations?.stations ?? [], q), [stations, q]);
  const set = (id: string) => {
    const other = compare[slot === 0 ? 1 : 0];
    if (other === id) return; // already picked in the other slot
    const next: [string | null, string | null] = [...compare] as [string | null, string | null];
    next[slot] = id;
    useApp.setState({ compare: next });
    setQ("");
    setOpen(false);
  };
  return (
    <div className="picker">
      {value ? <strong>{value.name}</strong> : <em className="faint">未選択</em>}
      <input
        placeholder="駅名…"
        value={q}
        onChange={e => { setQ(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={e => { if (e.key === "Escape") { setOpen(false); setQ(""); } }}
      />
      {open && hits.length > 0 && (
        <ul className="search-hits panel">
          {hits.map(s => (
            <li key={s.id}>
              <button onMouseDown={() => set(s.id)}>{s.name}</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const ROWS: { label: string; get: (s: Station) => string }[] = [
  { label: "㎡単価（中央値）", get: s => `${formatMan(s.metrics.median_ppsm)}円` },
  { label: "1年成長", get: s => formatPct(s.metrics.growth_1y) },
  { label: "取引数（4Q）", get: s => `${s.metrics.tx_count}件` },
  { label: "ハザード", get: s => s.metrics.hazard_score?.toFixed(0) ?? "—" },
  { label: "人口レジリエンス", get: s => s.metrics.pop_resilience != null ? `p${s.metrics.pop_resilience.toFixed(0)}` : "—" },
  { label: "ラベル", get: s => s.label },
];

export function CompareScreen() {
  const { stations, compare } = useApp();
  const all = useMemo(() => stations?.stations ?? [], [stations]);
  const a = all.find(s => s.id === compare[0]) ?? null;
  const b = all.find(s => s.id === compare[1]) ?? null;

  const [axA, axB] = useMemo(
    () => [a ? axesFor(a, all) : null, b ? axesFor(b, all) : null],
    [a, b, all],
  );

  const radarData = AXES.map((ax, i) => ({
    axis: ax.label,
    a: axA?.[i].value ?? 0,
    b: axB?.[i].value ?? 0,
  }));

  const prose = useMemo(
    () => (a && b && axA && axB ? proseFor(a, b, axA, axB) : []),
    [a, b, axA, axB],
  );

  return (
    <div className="compare">
      <div className="compare-pickers">
        <StationPicker slot={0} value={a} />
        <span className="faint">と</span>
        <StationPicker slot={1} value={b} />
      </div>

      {a && b ? (
        <div className="compare-body">
          <div className="panel" style={{ padding: 16 }}>
            <div style={{ display: "flex", justifyContent: "center", gap: 18, fontSize: 13 }}>
              <span style={{ color: "var(--accent)" }}>● {a.name}</span>
              <span style={{ color: "#6f9bd8" }}>● {b.name}</span>
            </div>
            <div style={{ height: 300 }}>
              <ResponsiveContainer>
                <RadarChart data={radarData} outerRadius="75%">
                  <PolarGrid stroke="#1e2a4a" />
                  <PolarAngleAxis dataKey="axis" tick={{ fontSize: 10, fill: "#9fb0d8" }} />
                  <Radar dataKey="a" stroke="#c9a86a" fill="#c9a86a" fillOpacity={0.18} />
                  <Radar dataKey="b" stroke="#6f9bd8" fill="#6f9bd8" fillOpacity={0.18} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div>
            <table className="compare-table panel">
              <thead>
                <tr>
                  <th />
                  <th style={{ color: "var(--accent)" }}>{a.name}</th>
                  <th style={{ color: "#6f9bd8" }}>{b.name}</th>
                </tr>
              </thead>
              <tbody>
                {ROWS.map(r => (
                  <tr key={r.label}>
                    <td>{r.label}</td>
                    <td>{r.get(a)}</td>
                    <td>{r.get(b)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="panel" style={{ padding: 14, marginTop: 12, fontSize: 13, lineHeight: 1.8, color: "var(--dim)" }}>
              {prose.map((line, i) => <p key={i} style={{ margin: 0 }}>{line}</p>)}
            </div>
          </div>
        </div>
      ) : (
        <p className="dim" style={{ marginTop: 24 }}>
          2つの駅を選ぶと比較が表示されます。地図の駅カードから「比較に追加」もできます。
        </p>
      )}
    </div>
  );
}
