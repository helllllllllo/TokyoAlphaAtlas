import { lensByKey } from "../lib/lenses";
import { useApp } from "../store";

export function Legend() {
  const lens = useApp(s => s.lens);
  const meta = useApp(s => s.meta);
  const l = lensByKey(lens);
  const gradient = `linear-gradient(90deg, ${l.ramp.join(", ")})`;
  return (
    <div className="legend panel">
      <div style={{ background: gradient, height: 8, borderRadius: 4 }} />
      <div className="legend-row">
        <span>{l.legend}</span>
      </div>
      <div className="legend-row faint">
        大きさ＝取引量　○＝データ薄　|　中古マンション・23区
      </div>
      <div className="legend-row faint">データ: {meta?.asof ?? "—"} まで</div>
    </div>
  );
}
