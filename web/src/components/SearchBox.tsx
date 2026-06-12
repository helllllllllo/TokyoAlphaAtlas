import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../store";
import type { Station } from "../types";

export function matchStations(stations: Station[], q: string): Station[] {
  const query = q.trim();
  if (!query) return [];
  const pre: Station[] = [];
  const sub: Station[] = [];
  for (const s of stations) {
    if (s.name.startsWith(query)) pre.push(s);
    else if (s.name.includes(query) || s.ward.includes(query)) sub.push(s);
  }
  return [...pre, ...sub].slice(0, 8);
}

export function SearchBox() {
  const { stations, select } = useApp();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const blurTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const navigate = useNavigate();
  const hits = useMemo(() => matchStations(stations?.stations ?? [], q), [stations, q]);

  useEffect(() => () => { if (blurTimer.current) clearTimeout(blurTimer.current); }, []);

  const pick = (id: string) => {
    select(id);
    setQ("");
    setOpen(false);
    navigate("/");
  };

  return (
    <div className="search">
      <input
        placeholder="駅名で検索…"
        value={q}
        onChange={e => { setQ(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onBlur={() => {
          // delay so a click on an option still registers before the list closes
          blurTimer.current = setTimeout(() => setOpen(false), 150);
        }}
        onKeyDown={e => { if (e.key === "Escape") setOpen(false); }}
        aria-label="駅名で検索"
      />
      {open && hits.length > 0 && (
        <ul className="search-hits panel">
          {hits.map(s => (
            <li key={s.id}>
              <button onClick={() => pick(s.id)}>
                {s.name} <span className="faint">{s.ward}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
