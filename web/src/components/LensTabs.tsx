import { LENSES } from "../lib/lenses";
import { useApp } from "../store";

export function LensTabs() {
  const { lens, setLens } = useApp();
  return (
    <div className="lens-tabs">
      {LENSES.map(l => (
        <button
          key={l.key}
          className={l.key === lens ? "on" : ""}
          onClick={() => setLens(l.key)}
        >
          {l.label}
        </button>
      ))}
      <button className="soon" disabled title="再開発レンズは今後追加予定">再開発</button>
    </div>
  );
}
