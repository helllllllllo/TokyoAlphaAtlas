import { LENSES } from "../lib/lenses";
import { useApp } from "../store";

export function LensTabs() {
  const lens = useApp(s => s.lens);
  const setLens = useApp(s => s.setLens);
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
    </div>
  );
}
