import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { buildStationThesis, rankOpportunities, type OpportunityProfile } from "../lib/opportunities";
import { formatMan, formatPct } from "../lib/format";
import { listWatchedStations, toggleWatchedStation } from "../lib/watchlist";
import { useApp } from "../store";

const PROFILES: { key: OpportunityProfile; label: string }[] = [
  { key: "balanced", label: "総合" },
  { key: "value", label: "割安" },
  { key: "momentum", label: "勢い" },
  { key: "defensive", label: "低リスク" },
];

function scoreTone(score: number): "good" | "warn" | undefined {
  if (score >= 72) return "good";
  if (score < 48) return "warn";
  return undefined;
}

export function DiscoverScreen() {
  const { stations, select, addCompare } = useApp();
  const navigate = useNavigate();
  const all = stations?.stations ?? [];
  const [profile, setProfile] = useState<OpportunityProfile>("balanced");
  const [watched, setWatched] = useState(() => listWatchedStations());

  const ranked = useMemo(() => rankOpportunities(all, profile, 14), [all, profile]);
  const watchedStations = useMemo(
    () => watched.map(id => all.find(s => s.id === id)).filter(Boolean),
    [watched, all],
  );

  const toggle = (id: string) => setWatched(toggleWatchedStation(id));
  const openOnMap = (id: string) => {
    select(id);
    navigate("/");
  };

  return (
    <div className="discover">
      <div className="discover-head">
        <h1>発掘候補</h1>
        <div className="profile-tabs" role="tablist" aria-label="発掘プロファイル">
          {PROFILES.map(p => (
            <button
              key={p.key}
              className={p.key === profile ? "on" : ""}
              onClick={() => setProfile(p.key)}
              type="button"
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div className="discover-grid">
        <section className="opportunity-list">
          {ranked.map(item => {
            const s = item.station;
            const isWatched = watched.includes(s.id);
            const thesis = buildStationThesis(s)[0];
            return (
              <article className="panel opportunity-card" key={s.id}>
                <button className="opportunity-main" onClick={() => openOnMap(s.id)} type="button">
                  <span>
                    <strong>{s.name}</strong>
                    <span className="faint">{s.ward} / {s.label}</span>
                  </span>
                  <span className={`opportunity-score ${scoreTone(item.score) ?? ""}`}>
                    {item.score}
                  </span>
                </button>
                <p>{thesis}</p>
                <div className="opportunity-metrics">
                  <span>㎡ {formatMan(s.metrics.median_ppsm)}円</span>
                  <span>1Y {formatPct(s.metrics.growth_1y)}</span>
                  <span>取引 {s.metrics.tx_count}件</span>
                </div>
                <div className="driver-row">
                  {item.drivers.map(d => (
                    <span key={d.key}>{d.label} {d.value}</span>
                  ))}
                  {item.warnings.map(w => <span className="warn" key={w}>{w}</span>)}
                </div>
                <div className="opportunity-actions">
                  <button className="secondary" onClick={() => toggle(s.id)} type="button">
                    {isWatched ? "解除" : "ウォッチ"}
                  </button>
                  <button
                    className="primary"
                    onClick={() => {
                      addCompare(s.id);
                      navigate("/compare");
                    }}
                    type="button"
                  >
                    比較
                  </button>
                </div>
              </article>
            );
          })}
        </section>

        <aside className="panel watchlist-card">
          <div className="label">ウォッチリスト</div>
          {watchedStations.length === 0 ? (
            <p className="dim small">未登録</p>
          ) : (
            <div className="chips">
              {watchedStations.map(s => s && (
                <button key={s.id} className="chip" onClick={() => openOnMap(s.id)} type="button">
                  {s.name}
                </button>
              ))}
            </div>
          )}
          {watchedStations.length >= 2 && (
            <button
              className="primary watch-compare"
              onClick={() => {
                useApp.setState({ compare: [watchedStations[0]?.id ?? null, watchedStations[1]?.id ?? null] });
                navigate("/compare");
              }}
              type="button"
            >
              上位2件を比較
            </button>
          )}
        </aside>
      </div>
    </div>
  );
}
