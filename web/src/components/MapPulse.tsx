import { useMemo } from "react";
import {
  buildLabelComposition,
  buildMapPulse,
  buildMapSpotlights,
  buildStationMicrostructure,
} from "../lib/mapInsights";
import { lensByKey } from "../lib/lenses";
import { formatMan } from "../lib/format";
import { useApp } from "../store";
import type { StationDetail } from "../types";

const LABEL_COLORS: Record<string, string> = {
  "標準": "#5a6890",
  "割安": "#7fe8a8",
  "データ薄": "#48598a",
  "モメンタム": "#f07c64",
  "プレミアム": "#c9a86a",
  "安定コア": "#7fd4ef",
};

export function MapPulse({ selectedDetail }: { selectedDetail?: StationDetail | null }) {
  const { stations, quarters, quarterIdx, lens, select, selectedId } = useApp();
  const activeLens = lensByKey(lens);
  const pulse = useMemo(() => (
    stations && quarters ? buildMapPulse(stations.stations, quarters, quarterIdx) : null
  ), [stations, quarters, quarterIdx]);
  const spotlights = useMemo(() => (
    stations ? buildMapSpotlights(stations.stations, activeLens, 5) : []
  ), [stations, activeLens]);
  const composition = useMemo(() => (
    stations ? buildLabelComposition(stations.stations) : []
  ), [stations]);
  const micro = useMemo(() => (
    selectedDetail ? buildStationMicrostructure(selectedDetail) : null
  ), [selectedDetail]);
  const selectedName = selectedId && stations?.stations.find(station => station.id === selectedId)?.name;

  if (!pulse) return null;

  return (
    <div className="map-pulse panel">
      <div className="pulse-stats">
        <div>
          <span className="label">Market Pulse</span>
          <strong>{pulse.quarter}</strong>
        </div>
        <div>
          <span className="label">中央値</span>
          <strong>{formatMan(pulse.medianPpsm)}円/㎡</strong>
        </div>
        <div>
          <span className="label">観測駅</span>
          <strong>{pulse.activeStations}</strong>
        </div>
        <div>
          <span className="label">取引</span>
          <strong>{pulse.totalTransactions.toLocaleString("ja-JP")}</strong>
        </div>
      </div>

      <div className="label-strip" aria-label="ラベル構成">
        {composition.map(item => (
          <span
            key={item.label}
            style={{
              width: `${Math.max(item.share * 100, 3)}%`,
              background: LABEL_COLORS[item.label] ?? "#5a6890",
            }}
            title={`${item.label}: ${item.count}駅`}
          />
        ))}
      </div>

      <div className="pulse-spotlights">
        {spotlights.map(item => (
          <button key={item.station.id} onClick={() => select(item.station.id)} type="button">
            <span>{item.station.name}</span>
            <strong>{item.formatted}</strong>
          </button>
        ))}
      </div>

      {micro && selectedName && (
        <div className="micro-panel">
          <div className="micro-head">
            <span className="label">{selectedName} Microstructure</span>
            <strong>{micro.trend === "up" ? "上昇基調" : micro.trend === "down" ? "下落基調" : micro.trend === "flat" ? "横ばい" : "判定なし"}</strong>
          </div>
          {micro.histBars.length > 0 && (
            <div className="micro-bars" aria-label="直近価格分布">
              {micro.histBars.map((bar, idx) => (
                <span key={idx} style={{ height: `${Math.max(bar.height * 100, 4)}%` }} title={`${bar.count}件`} />
              ))}
            </div>
          )}
          {micro.peerGaps.length > 0 && (
            <div className="peer-gaps">
              {micro.peerGaps.slice(0, 4).map(peer => (
                <div key={peer.name}>
                  <span>{peer.name}</span>
                  <i className={peer.tone} style={{ width: `${Math.max(peer.width * 100, 6)}%` }} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
