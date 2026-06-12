import { useEffect, useRef, useState } from "react";
import { useApp } from "../store";

export function TimeSlider() {
  const { quarters, quarterIdx, setQuarter, lens } = useApp();
  const [playing, setPlaying] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const n = quarters?.quarters.length ?? 0;
  const enabled = lens === "price" && n > 1;
  const idx = quarterIdx ?? n - 1;

  useEffect(() => {
    if (!playing || !enabled) return;
    timer.current = setInterval(() => {
      const cur = useApp.getState().quarterIdx ?? n - 1;
      const next = cur + 1;
      if (next >= n - 1) {
        useApp.getState().setQuarter(null);
        setPlaying(false);
      } else {
        useApp.getState().setQuarter(next);
      }
    }, 350);
    return () => { if (timer.current) clearInterval(timer.current); };
  }, [playing, enabled, n]);

  if (!quarters) return null;
  return (
    <div className={`time-slider panel${enabled ? "" : " disabled"}`}>
      <button
        className="play"
        disabled={!enabled}
        onClick={() => {
          if (!playing && quarterIdx == null) setQuarter(0);
          setPlaying(p => !p);
        }}
        aria-label={playing ? "停止" : "再生"}
      >
        {playing ? "■" : "▶"}
      </button>
      <input
        type="range"
        min={0}
        max={n - 1}
        value={idx}
        disabled={!enabled}
        onChange={e => {
          const v = Number(e.target.value);
          setQuarter(v === n - 1 ? null : v);
        }}
      />
      <span className="q-label">
        {quarters.quarters[idx]}
        {quarterIdx == null ? "（最新）" : ""}
      </span>
      {!enabled && <span className="q-hint">時間スクラブは価格レンズのみ</span>}
    </div>
  );
}
