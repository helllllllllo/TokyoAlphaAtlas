import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Bar, BarChart, ReferenceLine, ResponsiveContainer, XAxis, YAxis,
} from "recharts";
import { fetchDetail } from "../lib/data";
import { evaluateDeal, type DealResult } from "../lib/benchmark";
import { listDeals, removeDeal, saveDeal, type SavedDeal } from "../lib/deals";
import { formatMan } from "../lib/format";
import { useApp } from "../store";
import type { Hist } from "../types";

export function BenchmarkScreen() {
  const { stations } = useApp();
  const [params] = useSearchParams();
  const [stationId, setStationId] = useState(params.get("station") ?? "");
  const [priceMan, setPriceMan] = useState("");
  const [size, setSize] = useState("");
  const [builtYear, setBuiltYear] = useState("");
  const [rentMan, setRentMan] = useState("");
  const [hist, setHist] = useState<Hist | null>(null);
  const [result, setResult] = useState<DealResult | null>(null);
  const [deals, setDeals] = useState<SavedDeal[]>(listDeals());

  const station = stations?.stations.find(s => s.id === stationId) ?? null;

  useEffect(() => {
    if (!stationId) return;
    void fetchDetail(stationId).then(d => setHist(d?.hist ?? null));
  }, [stationId]);

  const histRows = useMemo(() => {
    if (!hist) return [];
    return hist.counts.map((c, i) => ({
      bin: formatMan((hist.bin_edges[i] + hist.bin_edges[i + 1]) / 2),
      count: c,
      mid: (hist.bin_edges[i] + hist.bin_edges[i + 1]) / 2,
    }));
  }, [hist]);

  const run = () => {
    if (!station || !priceMan || !size) return;
    const deal = {
      priceYen: Number(priceMan) * 10000,
      sizeM2: Number(size),
      builtYear: builtYear ? Number(builtYear) : undefined,
      rentYenMonthly: rentMan ? Number(rentMan) * 10000 : undefined,
    };
    setResult(evaluateDeal(deal, station, hist));
  };

  const save = () => {
    if (!station || !priceMan || !size) return;
    saveDeal({
      stationId: station.id,
      priceYen: Number(priceMan) * 10000,
      sizeM2: Number(size),
      builtYear: builtYear ? Number(builtYear) : undefined,
      rentYenMonthly: rentMan ? Number(rentMan) * 10000 : undefined,
    });
    setDeals(listDeals());
  };

  return (
    <div className="benchmark">
      <div className="panel bench-form">
        <h3>物件を査定する <span className="faint">中古マンション</span></h3>
        <div className="form-grid">
          <label>駅
            <select value={stationId} onChange={e => setStationId(e.target.value)}>
              <option value="">選択…</option>
              {stations?.stations.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </label>
          <label>価格（万円）<input inputMode="numeric" value={priceMan} onChange={e => setPriceMan(e.target.value)} /></label>
          <label>専有面積（㎡）<input inputMode="decimal" value={size} onChange={e => setSize(e.target.value)} /></label>
          <label>築年（西暦）<input inputMode="numeric" value={builtYear} onChange={e => setBuiltYear(e.target.value)} /></label>
          <label>想定家賃（万円/月・任意）<input inputMode="decimal" value={rentMan} onChange={e => setRentMan(e.target.value)} /></label>
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button className="primary" onClick={run} disabled={!station || !priceMan || !size}>査定する</button>
          <button className="secondary" onClick={save} disabled={!station || !priceMan || !size}>保存</button>
        </div>
      </div>

      {result && station && (
        <div className="panel bench-result">
          {hist ? (
            <div style={{ height: 160 }}>
              <ResponsiveContainer>
                <BarChart data={histRows} margin={{ top: 10, right: 8, bottom: 0, left: 0 }}>
                  <XAxis dataKey="bin" tick={{ fontSize: 9, fill: "#7a8ab8" }} />
                  <YAxis tick={{ fontSize: 9, fill: "#7a8ab8" }} width={24} />
                  <Bar dataKey="count" fill="#3f6fa0" />
                  <ReferenceLine
                    x={histRows.reduce((best, r) => Math.abs(r.mid - result.ppsm) < Math.abs(best.mid - result.ppsm) ? r : best, histRows[0])?.bin}
                    stroke="#c9a86a" strokeWidth={2}
                    label={{ value: "この物件", fill: "#c9a86a", fontSize: 11, position: "top" }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="dim small">この駅は分布表示に足る直近取引がありません（中央値ベースの判定のみ）。</p>
          )}
          <ul className="verdicts">
            {result.verdicts.map((v, i) => <li key={i}>{v}</li>)}
          </ul>
        </div>
      )}

      {deals.length > 0 && (
        <div className="panel bench-saved">
          <h4>保存した物件</h4>
          <ul>
            {deals.map(d => (
              <li key={d.id}>
                <span>{stations?.stations.find(s => s.id === d.stationId)?.name ?? d.stationId}</span>
                <span>{formatMan(d.priceYen / d.sizeM2)}円/㎡</span>
                <span className="faint">{d.sizeM2}㎡ {d.builtYear ? `築${d.builtYear}` : ""}</span>
                <button className="chip" onClick={() => { removeDeal(d.id); setDeals(listDeals()); }}>削除</button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
