import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchDetail } from "../lib/data";
import { formatMan, formatPct } from "../lib/format";
import { buildStationMicrostructure } from "../lib/mapInsights";
import { buildStationThesis } from "../lib/opportunities";
import { listWatchedStations, toggleWatchedStation } from "../lib/watchlist";
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
  if (d.embankment != null) parts.push(`盛土 ${(d.embankment * 100).toFixed(0)}%`);
  if (d.danger_zone != null) parts.push(d.danger_zone ? "災害危険区域あり" : "災害危険区域なし");
  return parts.join("・");
}

function redevelopmentText(d: StationDetail["redevelopment"]): string {
  if (!d) return "再開発シグナルなし";
  const parts: string[] = [];
  if (d.zoning?.use_area) {
    parts.push(`${d.zoning.use_area}${d.zoning.floor_area_ratio != null ? ` FAR${d.zoning.floor_area_ratio.toFixed(0)}%` : ""}`);
  }
  if (d.district_plan.count != null) parts.push(`地区計画 ${d.district_plan.count}件`);
  if (d.high_utilization.count != null) parts.push(`高度利用 ${d.high_utilization.count}件`);
  if (d.city_roads.count != null) parts.push(`都市計画道路 ${d.city_roads.count}件`);
  if (d.landprice_trend != null) parts.push(`地価 ${formatPct(d.landprice_trend)}`);
  if (d.population_trend != null) parts.push(`人口 ${formatPct(d.population_trend)}`);
  return parts.join("・") || "再開発シグナルなし";
}

export function StationCard() {
  const { selectedId, select, stations, addCompare } = useApp();
  const [detail, setDetail] = useState<StationDetail | null | "loading">("loading");
  const [watched, setWatched] = useState(() => listWatchedStations());
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
  const thesis = buildStationThesis(station);
  const isWatched = watched.includes(station.id);

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
        <Stat label="再開発" value={m.redevelopment_score != null ? m.redevelopment_score.toFixed(0) : "—"} tone={m.redevelopment_score != null && m.redevelopment_score >= 70 ? "good" : undefined} />
        <Stat label="計画密度" value={m.planning_intensity != null ? m.planning_intensity.toFixed(0) : "—"} />
      </div>

      <div className="memo-block">
        <div className="label">投資メモ</div>
        {thesis.map(line => <p key={line}>{line}</p>)}
      </div>

      {detail === "loading" ? (
        <p className="dim">詳細を読み込み中…</p>
      ) : detail == null ? (
        <p className="dim">この駅の詳細データが不足しています（データ不足）。</p>
      ) : (
        <>
          <div className="label" style={{ marginTop: 14 }}>㎡単価 四半期推移 ＋ 地価公示（点線）</div>
          <PriceChart detail={detail} />
          {(() => {
            const micro = buildStationMicrostructure(detail);
            return micro.histBars.length > 0 || micro.peerGaps.length > 0 ? (
              <div className="card-micro">
                <div className="micro-head">
                  <span className="label">市場マイクロ構造</span>
                  <strong>{micro.trend === "up" ? "上昇基調" : micro.trend === "down" ? "下落基調" : micro.trend === "flat" ? "横ばい" : "判定なし"}</strong>
                </div>
                {micro.histBars.length > 0 && (
                  <div className="micro-bars tall" aria-label="直近価格分布">
                    {micro.histBars.map((bar, idx) => (
                      <span key={idx} style={{ height: `${Math.max(bar.height * 100, 4)}%` }} title={`${bar.count}件`} />
                    ))}
                  </div>
                )}
                {micro.peerGaps.length > 0 && (
                  <div className="peer-gaps">
                    {micro.peerGaps.slice(0, 5).map(peer => (
                      <div key={peer.name}>
                        <span>{peer.name}</span>
                        <i className={peer.tone} style={{ width: `${Math.max(peer.width * 100, 6)}%` }} />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : null;
          })()}
          <div className="label" style={{ marginTop: 10 }}>ハザード内訳</div>
          <p className="dim small">{hazardText(detail.hazard)}</p>
          <div className="label" style={{ marginTop: 10 }}>再開発シグナル</div>
          <p className="dim small">{redevelopmentText(detail.redevelopment)}</p>
          {detail.redevelopment && (
            <div className="chips">
              <span className="chip">代理案件 {detail.redevelopment.projects_proxy}件</span>
              <span className="chip">スコア {detail.redevelopment.score.toFixed(0)}</span>
              {detail.redevelopment.zoning && <span className="chip">用途強度 {detail.redevelopment.zoning.intensity.toFixed(0)}</span>}
            </div>
          )}
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
        <button className="secondary" onClick={() => setWatched(toggleWatchedStation(station.id))}>
          {isWatched ? "ウォッチ解除" : "ウォッチ"}
        </button>
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
