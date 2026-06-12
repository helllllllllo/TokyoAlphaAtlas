import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchDetail } from "../lib/data";
import { formatMan, formatPct } from "../lib/format";
import { useApp } from "../store";
import type { Station, StationDetail } from "../types";
import { PriceChart } from "./PriceChart";

function Stat({ label, value, tone }: { label: string; value: string; tone?: "good" | "warn" }) {
  return (
    <div className="stat">
      <div className="label">{label}</div>
      <div className={`stat-v ${tone ?? ""}`}>{value}</div>
    </div>
  );
}

function hazardText(d: StationDetail["hazard"]): string {
  if (!d) return "ハザード情報なし";
  const parts: string[] = [];
  if (d.flood != null) parts.push(`洪水 ${(d.flood * 100).toFixed(0)}%圏`);
  if (d.landslide != null) parts.push(d.landslide ? "土砂警戒区域あり" : "土砂警戒なし");
  parts.push(d.liquefaction != null ? `液状化 ${(d.liquefaction * 100).toFixed(0)}%圏` : "液状化 データなし");
  return parts.join("・");
}

export function StationCard() {
  const { selectedId, select, stations, addCompare } = useApp();
  const [detail, setDetail] = useState<StationDetail | null | "loading">("loading");
  const navigate = useNavigate();
  const station: Station | undefined = stations?.stations.find(s => s.id === selectedId);

  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setDetail("loading");
    void fetchDetail(selectedId).then(d => { if (!cancelled) setDetail(d); });
    return () => { cancelled = true; };
  }, [selectedId]);

  if (!selectedId || !station) return null;
  const m = station.metrics;

  return (
    <aside className="station-card panel">
      <header>
        <div>
          <h2>{station.name} <span className="ward">{station.ward}</span></h2>
          <div className="lines">{station.lines.join("・")}</div>
        </div>
        <div>
          <span className="tag">{station.label}</span>
          <button className="close" onClick={() => select(null)} aria-label="閉じる">×</button>
        </div>
      </header>

      <div className="stat-grid">
        <Stat label="㎡単価（中央値）" value={`${formatMan(m.median_ppsm)}円`} />
        <Stat label="1年成長" value={formatPct(m.growth_1y)} tone={m.growth_1y != null && m.growth_1y > 0 ? "good" : undefined} />
        <Stat label="取引数（4Q）" value={`${m.tx_count}件`} />
        <Stat label="3年/5年成長" value={`${formatPct(m.growth_3y)} / ${formatPct(m.growth_5y)}`} />
        <Stat label="ハザード" value={m.hazard_score != null ? m.hazard_score.toFixed(0) : "—"} tone={m.hazard_score != null && m.hazard_score > 50 ? "warn" : undefined} />
        <Stat label="人口レジリエンス" value={m.pop_resilience != null ? `p${m.pop_resilience.toFixed(0)}` : "—"} />
      </div>

      {detail === "loading" ? (
        <p className="dim">詳細を読み込み中…</p>
      ) : detail == null ? (
        <p className="dim">この駅の詳細データが不足しています（データ不足）。</p>
      ) : (
        <>
          <div className="label" style={{ marginTop: 14 }}>㎡単価 四半期推移 ＋ 地価公示（点線）</div>
          <PriceChart detail={detail} />
          <div className="label" style={{ marginTop: 10 }}>ハザード内訳</div>
          <p className="dim small">{hazardText(detail.hazard)}</p>
          {(() => {
            const cheaper = detail.similar.filter(s => s.price_gap != null && s.price_gap < 0).slice(0, 5);
            return cheaper.length > 0 ? (
              <>
                <div className="label" style={{ marginTop: 10 }}>似てるのに安い駅</div>
                <div className="chips">
                  {cheaper.map(s => (
                    <button key={s.id} className="chip" onClick={() => select(s.id)}>
                      {s.name} {formatPct(s.price_gap)}
                    </button>
                  ))}
                </div>
              </>
            ) : null;
          })()}
        </>
      )}

      <div className="card-actions">
        <button className="primary" onClick={() => { addCompare(station.id); navigate("/compare"); }}>
          比較に追加
        </button>
        <button className="secondary" onClick={() => navigate(`/benchmark?station=${encodeURIComponent(station.id)}`)}>
          この駅で査定
        </button>
      </div>
    </aside>
  );
}
