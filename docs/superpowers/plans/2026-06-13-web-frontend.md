# Tokyo Alpha Atlas — Plan 2: Web Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the static Japanese-UI web app (地図 / 駅カード / 比較 / 査定) that reads the pipeline's JSON artifacts from `web/public/data/`.

**Architecture:** Vite + React + TypeScript SPA, no backend. MapLibre GL renders a dark Tokyo basemap with one circle per station (color = lens metric, radius = transaction volume, hollow gray = low confidence). All analytics logic lives in pure modules under `src/lib/` (vitest-tested); components stay thin. App-wide state (lens, quarter, selection, compare picks, loaded data) in one Zustand store. Saved deals in localStorage.

**Tech Stack:** Vite 6, React 18, TypeScript, MapLibre GL JS 5 (NO deck.gl), Zustand 5, Recharts 2, React Router 7, vitest (+jsdom), Playwright (smoke only).

**Spec:** `docs/superpowers/specs/2026-06-12-tokyo-alpha-atlas-design.md` §5–§7.
**Artifact shapes:** pinned in `pipeline/atlas/schemas.py`; generated locally by Task 3.

**Working directories:** `web/` for all `npm` commands; `pipeline/` for `uv`/`make` commands.

**Design tokens (used throughout):** bg `#0a0f1e`, panel `#0d1426`, border `#1a2440`, text `#e8eeff`, dim `#9fb0d8`, faint `#7a8ab8`, accent `#c9a86a`, good `#7fe8a8`, warn `#d8a05f`. Tone: refined analyst tool — no emoji in UI strings, no game language.

---

### Task 1: Scaffold the web app

**Files:**
- Create: `web/package.json`, `web/vite.config.ts`, `web/tsconfig.json`, `web/index.html`
- Create: `web/src/main.tsx`, `web/src/App.tsx`, `web/src/components/TopBar.tsx`, `web/src/styles.css`, `web/src/config.ts`
- Create: `web/src/lib/placeholder.test.ts` (deleted in Task 4)

- [ ] **Step 1: Create `web/package.json`**

```json
{
  "name": "atlas-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "dependencies": {
    "maplibre-gl": "^5.0.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^7.1.1",
    "recharts": "^2.15.0",
    "zustand": "^5.0.2"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "jsdom": "^25.0.1",
    "typescript": "~5.6.3",
    "vite": "^6.0.5",
    "vitest": "^2.1.8"
  }
}
```

- [ ] **Step 2: Create `web/vite.config.ts`**

```ts
/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
```

- [ ] **Step 3: Create `web/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noEmit": true,
    "skipLibCheck": true,
    "types": ["vite/client", "vitest/globals"]
  },
  "include": ["src"]
}
```

Note: `"types"` includes `vitest/globals` — also set `test.globals: true`? No: we import `describe/it/expect` explicitly from `vitest` in every test, so remove `"vitest/globals"` from types. Final `types`: `["vite/client"]`.

- [ ] **Step 4: Create `web/index.html`**

```html
<!doctype html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Tokyo Alpha Atlas</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Create `web/src/config.ts`**

```ts
export const MAP_STYLE =
  "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
export const INITIAL_CENTER: [number, number] = [139.75, 35.68];
export const INITIAL_ZOOM = 10.5;
export const SUPPORTED_SCHEMA_VERSION = 1;
export const DATA_BASE = `${import.meta.env.BASE_URL}data`;
```

- [ ] **Step 6: Create `web/src/styles.css`**

```css
:root {
  --bg: #0a0f1e; --panel: #0d1426; --border: #1a2440;
  --text: #e8eeff; --dim: #9fb0d8; --faint: #7a8ab8;
  --accent: #c9a86a; --good: #7fe8a8; --warn: #d8a05f;
  color-scheme: dark;
}
* { box-sizing: border-box; }
html, body, #root { margin: 0; height: 100%; }
body {
  background: var(--bg); color: var(--text);
  font-family: "Hiragino Sans", "Noto Sans JP", system-ui, sans-serif;
  font-size: 14px;
}
.topbar {
  display: flex; align-items: center; gap: 24px; height: 46px;
  padding: 0 16px; background: rgba(8, 12, 24, 0.92);
  border-bottom: 1px solid var(--border); position: relative; z-index: 20;
}
.topbar .brand { font-weight: 600; letter-spacing: 0.5px; }
.topbar a { color: var(--faint); text-decoration: none; padding: 13px 2px; font-size: 13px; }
.topbar a.active { color: var(--text); border-bottom: 2px solid var(--accent); }
.screen { height: calc(100% - 46px); position: relative; }
.panel { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; }
button.primary {
  background: #1e3a5f; border: 1px solid #3f6fd0; border-radius: 8px;
  color: #bcd4ff; padding: 8px 14px; cursor: pointer; font-size: 13px;
}
button.secondary {
  background: #2f2410; border: 1px solid #b8862e; border-radius: 8px;
  color: var(--accent); padding: 8px 14px; cursor: pointer; font-size: 13px;
}
input, select {
  background: #101a33; border: 1px solid #2a3a60; border-radius: 8px;
  color: var(--text); padding: 6px 10px; font-size: 13px;
}
.label { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: var(--faint); }
```

- [ ] **Step 7: Create `web/src/components/TopBar.tsx`**

```tsx
import { NavLink } from "react-router-dom";

export function TopBar({ children }: { children?: React.ReactNode }) {
  const cls = ({ isActive }: { isActive: boolean }) => (isActive ? "active" : "");
  return (
    <nav className="topbar">
      <span className="brand">Tokyo Alpha Atlas</span>
      <NavLink to="/" end className={cls}>地図</NavLink>
      <NavLink to="/compare" className={cls}>比較</NavLink>
      <NavLink to="/benchmark" className={cls}>査定</NavLink>
      <div style={{ marginLeft: "auto" }}>{children}</div>
    </nav>
  );
}
```

- [ ] **Step 8: Create `web/src/App.tsx` and `web/src/main.tsx`**

```tsx
// web/src/App.tsx
import { Route, Routes } from "react-router-dom";
import { TopBar } from "./components/TopBar";

export default function App() {
  return (
    <>
      <TopBar />
      <div className="screen">
        <Routes>
          <Route path="/" element={<p style={{ padding: 20 }}>地図（実装中）</p>} />
          <Route path="/compare" element={<p style={{ padding: 20 }}>比較（実装中）</p>} />
          <Route path="/benchmark" element={<p style={{ padding: 20 }}>査定（実装中）</p>} />
        </Routes>
      </div>
    </>
  );
}
```

```tsx
// web/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
```

- [ ] **Step 9: Create `web/src/lib/placeholder.test.ts`** (so vitest has a test; removed in Task 4)

```ts
import { describe, expect, it } from "vitest";

describe("scaffold", () => {
  it("runs", () => expect(1 + 1).toBe(2));
});
```

- [ ] **Step 10: Install, test, build**

Run: `cd web && npm install && npm test && npm run build`
Expected: 1 test passed; `vite build` completes with `dist/` output, no TS errors.

- [ ] **Step 11: Commit**

```bash
git add web/package.json web/package-lock.json web/vite.config.ts web/tsconfig.json web/index.html web/src
git commit -m "feat(web): scaffold Vite+React app shell with routing and design tokens"
```

---

### Task 2: Pipeline addition — price histogram + CLI fixture flags

**Files:**
- Modify: `pipeline/atlas/emit.py` (detail docs gain `hist`)
- Modify: `pipeline/atlas/schemas.py` (DETAIL_SCHEMA gains `hist`)
- Modify: `pipeline/atlas/config.py` (constants)
- Modify: `pipeline/atlas/cli.py` (argparse flags for all refresh params)
- Test: `pipeline/tests/test_emit.py` (new tests)

The 査定 screen positions a deal on the station's actual trailing-8Q price distribution. Medians alone can't do that, so detail docs gain a histogram. Age-band adjustment from the spec is explicitly deferred (post-MVP; needs an age-band table artifact).

- [ ] **Step 1: Write the failing tests** (append to `pipeline/tests/test_emit.py`)

```python
def test_detail_includes_histogram(prepared):
    con, report, out = prepared
    emit.emit_all(con, report, out_dir=out)
    detail = json.loads((out / "station" / "中野.json").read_text())
    h = detail["hist"]
    assert h["window_quarters"] == 8
    assert len(h["bin_edges"]) == len(h["counts"]) + 1
    # 中野 trailing 8Q = 26 designed + 2 survivors = 28 rows
    assert sum(h["counts"]) == 28
    assert min(h["bin_edges"]) <= 540000 <= max(h["bin_edges"])

def test_detail_hist_null_when_thin(prepared):
    con, report, out = prepared
    # synthetic thin station: 5 rows only — below HIST_MIN_TX
    con.execute("""
        insert into clean_transactions
        select '薄い駅', '中野区', qidx, quarter, ppsm, price, area, built_year, minutes, price_type
        from clean_transactions where station = '中野' limit 5
    """)
    con.execute("""
        insert into stations select '薄い駅', lon, lat, lines, n_lines, n_operators, ridership
        from stations where name_norm = '中野'
    """)
    emit.emit_all(con, report, out_dir=out)
    detail = json.loads((out / "station" / "薄い駅.json").read_text())
    assert detail["hist"] is None
```

Note: if the `stations` table in the fixture run carries extra augmentation columns (hazard etc.), adapt the synthetic insert to `select '薄い駅', * exclude(name_norm) from stations where name_norm='中野'` — DuckDB supports `EXCLUDE`. Use whichever matches the actual column set.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd pipeline && uv run pytest tests/test_emit.py -q`
Expected: FAIL — KeyError `'hist'`

- [ ] **Step 3: Implement.** In `pipeline/atlas/config.py` add:

```python
HIST_WINDOW_QUARTERS = 8
HIST_MIN_TX = 20
HIST_BINS = 12
```

In `pipeline/atlas/emit.py`, add a helper and wire it into `build_docs`:

```python
def _histograms(con, asof):
    """Per-station ppsm histogram over the trailing HIST_WINDOW_QUARTERS."""
    df = con.execute(
        "select station, ppsm from clean_transactions where qidx between ? and ?",
        [asof - config.HIST_WINDOW_QUARTERS + 1, asof],
    ).df()
    out = {}
    for st, g in df.groupby("station"):
        vals = g.ppsm.values
        if len(vals) < config.HIST_MIN_TX:
            out[st] = None
            continue
        counts, edges = np.histogram(vals, bins=config.HIST_BINS)
        out[st] = {
            "window_quarters": config.HIST_WINDOW_QUARTERS,
            "bin_edges": [float(e) for e in edges],
            "counts": [int(c) for c in counts],
        }
    return out
```

In `build_docs`, compute `hists = _histograms(con, asof)` and set `"hist": hists.get(<raw station name>, None)` in each detail doc (key by the raw name used in `clean_transactions`, not the safe id; zero-window stations get whatever the trailing-8Q window yields, which may be a real histogram — that is correct). In `pipeline/atlas/schemas.py` DETAIL_SCHEMA: add `"hist"` to `required` and properties:

```python
"hist": {"type": ["object", "null"]},
```

- [ ] **Step 4: Add CLI flags.** In `pipeline/atlas/cli.py` `main()`, add argparse options to the `refresh` subparser for every `refresh()` parameter that lacks one, mapping 1:1 (read the current `refresh()` signature first — it includes tx_dir, n02_path, s12_path, out_dir, db_path plus the hermetic geo paths added in the final-review hardening):

```python
p = sub.add_parser("refresh", help="run the full pipeline against data/raw/")
p.add_argument("--tx-dir", type=Path, default=None)
p.add_argument("--n02", type=Path, default=None)
p.add_argument("--s12", type=Path, default=None)
p.add_argument("--out-dir", type=Path, default=None)
p.add_argument("--db-path", type=Path, default=None)
# plus one flag per remaining refresh() geo param, named consistently
# (--hazard-dir / --population / --landprice-dir / --rail-src etc. to match the signature)
```

and pass them through in `main()`.

- [ ] **Step 5: Run full pipeline suite**

Run: `cd pipeline && uv run pytest -q`
Expected: all pass (76 + 2 new = 78)

- [ ] **Step 6: Commit**

```bash
git add pipeline/atlas pipeline/tests
git commit -m "feat(pipeline): trailing-8Q price histograms in detail docs; full CLI flags"
```

---

### Task 3: Dev data generation (`make dev-data`)

**Files:**
- Modify: `pipeline/Makefile`
- Modify: `.gitignore`

- [ ] **Step 1: Add to `.gitignore`** (repo root):

```
web/public/data/
web/node_modules/
web/dist/
```

`web/public/data/` stays untracked while it holds fixture data; once real artifacts land the line can be removed deliberately.

- [ ] **Step 2: Add `dev-data` target to `pipeline/Makefile`** (staging fixture hazard files into the names the CLI expects; adapt flag names to what Task 2 actually added):

```makefile
dev-data:
	mkdir -p /tmp/atlas-devraw/hazard
	cp tests/fixtures/a31_flood.geojson /tmp/atlas-devraw/hazard/flood.geojson
	cp tests/fixtures/a33_landslide.geojson /tmp/atlas-devraw/hazard/landslide.geojson
	uv run python -m atlas.cli refresh \
	  --tx-dir tests/fixtures/transactions \
	  --n02 tests/fixtures/n02_stations.geojson \
	  --s12 tests/fixtures/s12_ridership.geojson \
	  --hazard-dir /tmp/atlas-devraw/hazard \
	  --population tests/fixtures/pop_mesh.geojson \
	  --landprice-dir tests/fixtures/landprice \
	  --out-dir ../web/public/data \
	  --db-path /tmp/atlas-dev.duckdb
```

- [ ] **Step 3: Run it and verify**

Run: `cd pipeline && make dev-data && ls ../web/public/data`
Expected: refresh report prints (3 stations, asof 2023Q4); `stations.json quarters.json meta.json station/ hazard/` present. `cat ../web/public/data/stations.json | head -c 300` shows 中野 with metrics.

- [ ] **Step 4: Commit**

```bash
git add .gitignore pipeline/Makefile
git commit -m "feat(pipeline): make dev-data — fixture artifacts for frontend development"
```

---

### Task 4: Types + formatting utilities

**Files:**
- Create: `web/src/types.ts`, `web/src/lib/format.ts`
- Test: `web/src/lib/format.test.ts`
- Delete: `web/src/lib/placeholder.test.ts`

- [ ] **Step 1: Create `web/src/types.ts`** (mirrors `pipeline/atlas/schemas.py`)

```ts
export interface StationMetrics {
  median_ppsm: number | null;
  tx_count: number;
  growth_1y: number | null;
  growth_3y: number | null;
  growth_5y: number | null;
  volatility: number | null;
  dispersion: number | null;
  liquidity_score: number;
  relative_value: number | null;
  hazard_score: number | null;
  pop_resilience: number | null;
  gravity: number;
  confidence: 0 | 1 | 2;
}

export interface Station {
  id: string;
  name: string;
  ward: string;
  lines: string[];
  lon: number;
  lat: number;
  label: string;
  metrics: StationMetrics;
}

export interface StationsDoc {
  schema_version: number;
  asof: string;
  stations: Station[];
}

export interface QuartersDoc {
  schema_version: number;
  quarters: string[];
  stations: Record<string, { m: (number | null)[]; n: number[] }>;
}

export interface SimilarStation {
  id: string;
  name: string;
  median_ppsm: number | null;
  price_gap: number | null;
}

export interface Hist {
  window_quarters: number;
  bin_edges: number[];
  counts: number[];
}

export interface StationDetail {
  schema_version: number;
  id: string;
  name: string;
  series: { quarters: string[]; median_ppsm: (number | null)[]; tx_count: number[] };
  similar: SimilarStation[];
  hazard: { flood: number | null; landslide: boolean | null; liquefaction: number | null } | null;
  landprice: { years: number[]; price: number[] } | null;
  hist: Hist | null;
}

export interface MetaDoc {
  schema_version: number;
  asof: string;
  generated_rows: Record<string, number | string>;
  sources: Record<string, unknown>;
}
```

- [ ] **Step 2: Write failing tests `web/src/lib/format.test.ts`**

```ts
import { describe, expect, it } from "vitest";
import { formatMan, formatPct, formatYen } from "./format";

describe("formatMan", () => {
  it("converts yen/m2 to 万円 with one decimal", () => {
    expect(formatMan(824000)).toBe("82.4万");
    expect(formatMan(1520000)).toBe("152.0万");
  });
  it("handles null", () => expect(formatMan(null)).toBe("—"));
});

describe("formatPct", () => {
  it("signs and rounds", () => {
    expect(formatPct(0.092)).toBe("+9.2%");
    expect(formatPct(-0.034)).toBe("−3.4%");
    expect(formatPct(0)).toBe("0.0%");
  });
  it("handles null", () => expect(formatPct(null)).toBe("—"));
});

describe("formatYen", () => {
  it("groups digits", () => expect(formatYen(33000000)).toBe("3,300万円"));
});
```

- [ ] **Step 3: Run to verify failure**

Run: `cd web && npm test`
Expected: FAIL — cannot resolve `./format`

- [ ] **Step 4: Implement `web/src/lib/format.ts`**

```ts
export function formatMan(yen: number | null): string {
  if (yen == null) return "—";
  return `${(yen / 10000).toFixed(1)}万`;
}

export function formatPct(x: number | null): string {
  if (x == null) return "—";
  const v = (x * 100).toFixed(1);
  if (x > 0) return `+${v}%`;
  if (x < 0) return `−${Math.abs(x * 100).toFixed(1)}%`;
  return `${v}%`;
}

export function formatYen(yen: number): string {
  return `${Math.round(yen / 10000).toLocaleString("ja-JP")}万円`;
}
```

- [ ] **Step 5: Delete placeholder, run, commit**

Run: `rm web/src/lib/placeholder.test.ts && cd web && npm test`
Expected: format tests pass.

```bash
git add web/src/types.ts web/src/lib/format.ts web/src/lib/format.test.ts
git rm web/src/lib/placeholder.test.ts 2>/dev/null; git add -u
git commit -m "feat(web): artifact types and Japanese number formatting"
```

---

### Task 5: Data loading layer

**Files:**
- Create: `web/src/lib/data.ts`
- Test: `web/src/lib/data.test.ts`

- [ ] **Step 1: Write failing tests `web/src/lib/data.test.ts`**

```ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { SchemaMismatchError, fetchDetail, fetchJson, fetchMeta } from "./data";

function mockFetch(map: Record<string, unknown>) {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    for (const [k, v] of Object.entries(map)) {
      if (url.endsWith(k)) {
        if (v === 404) return new Response("not found", { status: 404 });
        return new Response(JSON.stringify(v), { status: 200 });
      }
    }
    return new Response("not found", { status: 404 });
  }));
}

afterEach(() => vi.unstubAllGlobals());

describe("fetchJson", () => {
  it("throws on http error", async () => {
    mockFetch({});
    await expect(fetchJson("/data/nope.json")).rejects.toThrow(/404/);
  });
});

describe("fetchMeta", () => {
  it("accepts matching schema version", async () => {
    mockFetch({ "meta.json": { schema_version: 1, asof: "2023Q4", generated_rows: {}, sources: {} } });
    const meta = await fetchMeta();
    expect(meta.asof).toBe("2023Q4");
  });
  it("rejects mismatched schema version", async () => {
    mockFetch({ "meta.json": { schema_version: 99, asof: "2023Q4", generated_rows: {}, sources: {} } });
    await expect(fetchMeta()).rejects.toBeInstanceOf(SchemaMismatchError);
  });
});

describe("fetchDetail", () => {
  it("returns null on 404 and caches results", async () => {
    mockFetch({ "station/中野.json": { id: "中野" }, "station/無い.json": 404 });
    expect(await fetchDetail("無い")).toBeNull();
    const d1 = await fetchDetail("中野");
    const d2 = await fetchDetail("中野");
    expect(d1).toBe(d2); // same object → cached
    expect(vi.mocked(fetch).mock.calls.filter(c => String(c[0]).includes("中野")).length).toBe(1);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd web && npm test`
Expected: FAIL — cannot resolve `./data`

- [ ] **Step 3: Implement `web/src/lib/data.ts`**

```ts
import { DATA_BASE, SUPPORTED_SCHEMA_VERSION } from "../config";
import type { MetaDoc, QuartersDoc, StationDetail, StationsDoc } from "../types";

export class SchemaMismatchError extends Error {
  constructor(got: number) {
    super(`データのスキーマバージョン (${got}) がアプリ (${SUPPORTED_SCHEMA_VERSION}) と一致しません。`);
  }
}

export async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return (await res.json()) as T;
}

export async function fetchMeta(): Promise<MetaDoc> {
  const meta = await fetchJson<MetaDoc>(`${DATA_BASE}/meta.json`);
  if (meta.schema_version !== SUPPORTED_SCHEMA_VERSION) {
    throw new SchemaMismatchError(meta.schema_version);
  }
  return meta;
}

export const fetchStations = () => fetchJson<StationsDoc>(`${DATA_BASE}/stations.json`);
export const fetchQuarters = () => fetchJson<QuartersDoc>(`${DATA_BASE}/quarters.json`);

const detailCache = new Map<string, StationDetail | null>();

export async function fetchDetail(id: string): Promise<StationDetail | null> {
  if (detailCache.has(id)) return detailCache.get(id)!;
  const res = await fetch(`${DATA_BASE}/station/${encodeURIComponent(id)}.json`);
  const detail = res.ok ? ((await res.json()) as StationDetail) : null;
  detailCache.set(id, detail);
  return detail;
}
```

- [ ] **Step 4: Run tests, commit**

Run: `cd web && npm test`
Expected: all pass.

```bash
git add web/src/lib/data.ts web/src/lib/data.test.ts
git commit -m "feat(web): data loading with schema-version gate and detail cache"
```

---

### Task 6: Lenses and color scales

**Files:**
- Create: `web/src/lib/color.ts`, `web/src/lib/lenses.ts`
- Test: `web/src/lib/lenses.test.ts`

- [ ] **Step 1: Write failing tests `web/src/lib/lenses.test.ts`**

```ts
import { describe, expect, it } from "vitest";
import { lerpColor } from "./color";
import { LENSES, colorFor, lensByKey } from "./lenses";
import type { StationMetrics } from "../types";

const M: StationMetrics = {
  median_ppsm: 800000, tx_count: 100, growth_1y: 0.09, growth_3y: 0.2,
  growth_5y: 0.35, volatility: 0.03, dispersion: 0.2, liquidity_score: 80,
  relative_value: 0.12, hazard_score: 60, pop_resilience: 70, gravity: 75, confidence: 2,
};

describe("lerpColor", () => {
  it("interpolates hex", () => {
    expect(lerpColor("#000000", "#ffffff", 0.5)).toBe("#808080");
    expect(lerpColor("#ff0000", "#00ff00", 0)).toBe("#ff0000");
  });
});

describe("lenses", () => {
  it("has the five spec lenses in order", () => {
    expect(LENSES.map(l => l.key)).toEqual(["price", "momentum", "value", "liquidity", "risk"]);
    expect(lensByKey("price").label).toBe("価格");
  });
  it("accessors read the right metric", () => {
    expect(lensByKey("price").accessor(M)).toBe(800000);
    expect(lensByKey("momentum").accessor(M)).toBe(0.09);
    expect(lensByKey("risk").accessor(M)).toBe(60);
  });
  it("colorFor clamps to domain and returns gray for null", () => {
    const lens = lensByKey("price");
    expect(colorFor(lens, null)).toBe("#48598a");
    expect(colorFor(lens, -1)).toBe(colorFor(lens, lens.domain[0]));
    expect(colorFor(lens, 99e9)).toBe(colorFor(lens, lens.domain[1]));
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd web && npm test`
Expected: FAIL — cannot resolve `./lenses`

- [ ] **Step 3: Implement `web/src/lib/color.ts`**

```ts
export function lerpColor(a: string, b: string, t: number): string {
  const pa = parseInt(a.slice(1), 16);
  const pb = parseInt(b.slice(1), 16);
  const ch = (sh: number) => {
    const va = (pa >> sh) & 0xff;
    const vb = (pb >> sh) & 0xff;
    return Math.round(va + (vb - va) * t);
  };
  const hex = (v: number) => v.toString(16).padStart(2, "0");
  return `#${hex(ch(16))}${hex(ch(8))}${hex(ch(0))}`;
}

/** Map t in [0,1] onto a multi-stop ramp. */
export function rampColor(stops: string[], t: number): string {
  const x = Math.min(Math.max(t, 0), 1) * (stops.length - 1);
  const i = Math.min(Math.floor(x), stops.length - 2);
  return lerpColor(stops[i], stops[i + 1], x - i);
}
```

- [ ] **Step 4: Implement `web/src/lib/lenses.ts`**

```ts
import { rampColor } from "./color";
import type { StationMetrics } from "../types";

export type LensKey = "price" | "momentum" | "value" | "liquidity" | "risk";

export interface Lens {
  key: LensKey;
  label: string;
  legend: string;
  accessor: (m: StationMetrics) => number | null;
  domain: [number, number];
  ramp: string[]; // low → high
}

export const NULL_COLOR = "#48598a";

export const LENSES: Lens[] = [
  {
    key: "price", label: "価格", legend: "色＝㎡単価",
    accessor: m => m.median_ppsm, domain: [400_000, 2_000_000],
    ramp: ["#3f6fd0", "#9b4fc0", "#d85f7a", "#e0764f"],
  },
  {
    key: "momentum", label: "モメンタム", legend: "色＝1年成長率",
    accessor: m => m.growth_1y, domain: [-0.1, 0.15],
    ramp: ["#3a5fa0", "#5a7ab8", "#c9a86a", "#e0764f"],
  },
  {
    key: "value", label: "割安", legend: "色＝類似駅比の割安度",
    accessor: m => m.relative_value, domain: [-0.25, 0.25],
    ramp: ["#7a4060", "#5a6890", "#4fa080", "#7fe8a8"],
  },
  {
    key: "liquidity", label: "流動性", legend: "色＝取引量の厚さ",
    accessor: m => m.liquidity_score, domain: [0, 100],
    ramp: ["#2a3a60", "#3f6fa0", "#3fa3c4", "#7fd4ef"],
  },
  {
    key: "risk", label: "リスク", legend: "色＝ハザード（赤＝高）",
    accessor: m => m.hazard_score, domain: [0, 100],
    ramp: ["#3f8f6f", "#c9a86a", "#d8745f", "#c43f3f"],
  },
];

export function lensByKey(key: LensKey): Lens {
  return LENSES.find(l => l.key === key)!;
}

export function colorFor(lens: Lens, value: number | null): string {
  if (value == null) return NULL_COLOR;
  const [lo, hi] = lens.domain;
  return rampColor(lens.ramp, (value - lo) / (hi - lo));
}
```

- [ ] **Step 5: Run tests, commit**

Run: `cd web && npm test` — Expected: all pass.

```bash
git add web/src/lib/color.ts web/src/lib/lenses.ts web/src/lib/lenses.test.ts
git commit -m "feat(web): five lens definitions with color ramps"
```

---

### Task 7: App store (Zustand) + data bootstrapping

**Files:**
- Create: `web/src/store.ts`
- Test: `web/src/store.test.ts`
- Modify: `web/src/App.tsx` (load on mount; loading/error states)

- [ ] **Step 1: Write failing tests `web/src/store.test.ts`**

```ts
import { beforeEach, describe, expect, it } from "vitest";
import { useApp } from "./store";

beforeEach(() => {
  useApp.setState({
    lens: "price", quarterIdx: null, selectedId: null, compare: [null, null],
  });
});

describe("store", () => {
  it("switching lens away from price resets the quarter scrub", () => {
    useApp.getState().setQuarter(10);
    useApp.getState().setLens("momentum");
    expect(useApp.getState().quarterIdx).toBeNull();
  });
  it("addCompare fills slots then rotates", () => {
    const s = useApp.getState();
    s.addCompare("A");
    s.addCompare("B");
    s.addCompare("C");
    expect(useApp.getState().compare).toEqual(["B", "C"]);
  });
  it("addCompare ignores duplicates", () => {
    useApp.getState().addCompare("A");
    useApp.getState().addCompare("A");
    expect(useApp.getState().compare).toEqual(["A", null]);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd web && npm test` — Expected: FAIL — cannot resolve `./store`

- [ ] **Step 3: Implement `web/src/store.ts`**

```ts
import { create } from "zustand";
import { fetchMeta, fetchQuarters, fetchStations } from "./lib/data";
import type { LensKey } from "./lib/lenses";
import type { MetaDoc, QuartersDoc, StationsDoc } from "./types";

interface AppState {
  lens: LensKey;
  quarterIdx: number | null; // null = latest snapshot
  selectedId: string | null;
  compare: [string | null, string | null];
  status: "loading" | "ready" | "error";
  error: string | null;
  stations: StationsDoc | null;
  quarters: QuartersDoc | null;
  meta: MetaDoc | null;
  setLens: (l: LensKey) => void;
  setQuarter: (i: number | null) => void;
  select: (id: string | null) => void;
  addCompare: (id: string) => void;
  clearCompare: () => void;
  load: () => Promise<void>;
}

export const useApp = create<AppState>((set, get) => ({
  lens: "price",
  quarterIdx: null,
  selectedId: null,
  compare: [null, null],
  status: "loading",
  error: null,
  stations: null,
  quarters: null,
  meta: null,

  setLens: lens => set({ lens, quarterIdx: lens === "price" ? get().quarterIdx : null }),
  setQuarter: quarterIdx => set({ quarterIdx }),
  select: selectedId => set({ selectedId }),

  addCompare: id => {
    const [a, b] = get().compare;
    if (a === id || b === id) return;
    if (a == null) set({ compare: [id, b] });
    else if (b == null) set({ compare: [a, id] });
    else set({ compare: [b, id] });
  },
  clearCompare: () => set({ compare: [null, null] }),

  load: async () => {
    try {
      const meta = await fetchMeta();
      const [stations, quarters] = await Promise.all([fetchStations(), fetchQuarters()]);
      set({ meta, stations, quarters, status: "ready" });
    } catch (e) {
      set({ status: "error", error: e instanceof Error ? e.message : String(e) });
    }
  },
}));
```

- [ ] **Step 4: Wire into `web/src/App.tsx`** (replace entirely)

```tsx
import { useEffect } from "react";
import { Route, Routes } from "react-router-dom";
import { TopBar } from "./components/TopBar";
import { useApp } from "./store";

export default function App() {
  const { status, error, load } = useApp();
  useEffect(() => { void load(); }, [load]);

  if (status === "error") {
    return (
      <div style={{ display: "grid", placeItems: "center", height: "100%" }}>
        <div className="panel" style={{ padding: 32, maxWidth: 480 }}>
          <h2>データを読み込めません</h2>
          <p style={{ color: "var(--dim)" }}>{error}</p>
          <p style={{ color: "var(--faint)", fontSize: 12 }}>
            `pipeline/` で `make dev-data`（または実データで `make refresh`）を実行してから再読み込みしてください。
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <TopBar />
      <div className="screen">
        {status === "loading" ? (
          <p style={{ padding: 20, color: "var(--dim)" }}>読み込み中…</p>
        ) : (
          <Routes>
            <Route path="/" element={<p style={{ padding: 20 }}>地図（実装中）</p>} />
            <Route path="/compare" element={<p style={{ padding: 20 }}>比較（実装中）</p>} />
            <Route path="/benchmark" element={<p style={{ padding: 20 }}>査定（実装中）</p>} />
          </Routes>
        )}
      </div>
    </>
  );
}
```

- [ ] **Step 5: Run tests + build, commit**

Run: `cd web && npm test && npm run build` — Expected: all pass; build clean.

```bash
git add web/src/store.ts web/src/store.test.ts web/src/App.tsx
git commit -m "feat(web): zustand store with data bootstrap and error screen"
```

---

### Task 8: Map feature builder (pure logic)

**Files:**
- Create: `web/src/lib/mapData.ts`
- Test: `web/src/lib/mapData.test.ts`

- [ ] **Step 1: Write failing tests `web/src/lib/mapData.test.ts`**

```ts
import { describe, expect, it } from "vitest";
import { buildStationFeatures, radiusFor } from "./mapData";
import { lensByKey, NULL_COLOR } from "./lenses";
import type { QuartersDoc, Station } from "../types";

const station = (over: Partial<Station> = {}): Station => ({
  id: "中野", name: "中野", ward: "中野区", lines: ["中央線"], lon: 139.66, lat: 35.7,
  label: "モメンタム",
  metrics: {
    median_ppsm: 660000, tx_count: 100, growth_1y: 0.1, growth_3y: null, growth_5y: null,
    volatility: 0.03, dispersion: 0.2, liquidity_score: 80, relative_value: 0.05,
    hazard_score: 35, pop_resilience: 70, gravity: 75, confidence: 2,
  },
  ...over,
});

const quarters: QuartersDoc = {
  schema_version: 1,
  quarters: ["2023Q3", "2023Q4"],
  stations: { 中野: { m: [500000, 660000], n: [3, 5] } },
};

describe("radiusFor", () => {
  it("grows with sqrt of count and clamps", () => {
    expect(radiusFor(0)).toBe(4);
    expect(radiusFor(400)).toBe(16);
    expect(radiusFor(100)).toBeCloseTo(10, 0);
  });
});

describe("buildStationFeatures", () => {
  it("colors by snapshot metric at latest quarter", () => {
    const fc = buildStationFeatures([station()], quarters, lensByKey("price"), null);
    const p = fc.features[0].properties!;
    expect(p.id).toBe("中野");
    expect(p.color).not.toBe(NULL_COLOR);
    expect(p.opacity).toBeGreaterThan(0.8); // confidence 2
  });
  it("uses quarterly median when scrubbed on price lens", () => {
    const latest = buildStationFeatures([station()], quarters, lensByKey("price"), null);
    const past = buildStationFeatures([station()], quarters, lensByKey("price"), 0);
    expect(past.features[0].properties!.color).not.toBe(latest.features[0].properties!.color);
    expect(past.features[0].properties!.priceLabel).toContain("50.0万");
  });
  it("renders low confidence as hollow gray", () => {
    const s = station({ metrics: { ...station().metrics, confidence: 0, median_ppsm: null } });
    const fc = buildStationFeatures([s], quarters, lensByKey("price"), null);
    const p = fc.features[0].properties!;
    expect(p.opacity).toBeLessThan(0.15);
    expect(p.strokeWidth).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd web && npm test` — Expected: FAIL — cannot resolve `./mapData`

- [ ] **Step 3: Implement `web/src/lib/mapData.ts`**

```ts
import { colorFor, type Lens } from "./lenses";
import { formatMan, formatPct } from "./format";
import type { QuartersDoc, Station } from "../types";

export function radiusFor(txCount: number): number {
  return 4 + 12 * Math.sqrt(Math.min(txCount, 400) / 400);
}

export interface StationFeatureProps {
  id: string;
  name: string;
  color: string;
  radius: number;
  opacity: number;
  strokeWidth: number;
  strokeColor: string;
  labelText: string;
  priceLabel: string;
  growthLabel: string;
  txLabel: string;
}

export function buildStationFeatures(
  stations: Station[],
  quarters: QuartersDoc,
  lens: Lens,
  quarterIdx: number | null,
): GeoJSON.FeatureCollection<GeoJSON.Point, StationFeatureProps> {
  const features = stations.map(s => {
    const q = quarters.stations[s.id];
    const scrubbed = quarterIdx != null && lens.key === "price";
    const median = scrubbed ? (q?.m[quarterIdx] ?? null) : s.metrics.median_ppsm;
    const tx = scrubbed ? (q?.n[quarterIdx] ?? 0) : s.metrics.tx_count;
    const value = scrubbed ? median : lens.accessor(s.metrics);
    const conf = scrubbed ? (tx >= 10 ? 2 : tx >= 3 ? 1 : 0) : s.metrics.confidence;

    const opacity = conf === 2 ? 0.9 : conf === 1 ? 0.55 : 0.08;
    const priceLabel = `㎡単価 ${formatMan(median)}円`;
    return {
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [s.lon, s.lat] },
      properties: {
        id: s.id,
        name: s.name,
        color: colorFor(lens, value),
        radius: radiusFor(tx),
        opacity,
        strokeWidth: conf === 0 ? 1.5 : 0,
        strokeColor: "#48598a",
        labelText: `${s.name} ${formatMan(median)}`,
        priceLabel,
        growthLabel: `1年成長 ${formatPct(s.metrics.growth_1y)}`,
        txLabel: `取引 ${tx}件`,
      },
    };
  });
  return { type: "FeatureCollection", features };
}
```

Note: `GeoJSON` global types ship with `@types/geojson` via maplibre's dependency tree; if `tsc` complains, `npm i -D @types/geojson`.

- [ ] **Step 4: Run tests, commit**

Run: `cd web && npm test` — Expected: all pass.

```bash
git add web/src/lib/mapData.ts web/src/lib/mapData.test.ts
git commit -m "feat(web): pure station-feature builder for the map"
```

---

### Task 9: Map screen — basemap, circles, tooltip, click, legend

**Files:**
- Create: `web/src/screens/MapScreen.tsx`, `web/src/components/Legend.tsx`, `web/src/components/LensTabs.tsx`
- Modify: `web/src/App.tsx` (route), `web/src/styles.css` (map styles)

This task is verified visually (no map unit tests; logic was tested in Task 8).

- [ ] **Step 1: Create `web/src/components/LensTabs.tsx`**

```tsx
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
```

- [ ] **Step 2: Create `web/src/components/Legend.tsx`**

```tsx
import { lensByKey } from "../lib/lenses";
import { useApp } from "../store";

export function Legend() {
  const { lens, meta } = useApp();
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
```

- [ ] **Step 3: Create `web/src/screens/MapScreen.tsx`**

```tsx
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import { INITIAL_CENTER, INITIAL_ZOOM, MAP_STYLE } from "../config";
import { buildStationFeatures } from "../lib/mapData";
import { lensByKey } from "../lib/lenses";
import { useApp } from "../store";
import { Legend } from "../components/Legend";
import { LensTabs } from "../components/LensTabs";

const EMPTY: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

export function MapScreen() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const { stations, quarters, lens, quarterIdx, select, selectedId } = useApp();

  // init once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center: INITIAL_CENTER,
      zoom: INITIAL_ZOOM,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    const popup = new maplibregl.Popup({
      closeButton: false, closeOnClick: false, className: "station-tip", offset: 12,
    });

    map.on("load", () => {
      map.addSource("stations", { type: "geojson", data: EMPTY });
      map.addLayer({
        id: "station-circles", type: "circle", source: "stations",
        paint: {
          "circle-radius": ["get", "radius"],
          "circle-color": ["get", "color"],
          "circle-opacity": ["get", "opacity"],
          "circle-stroke-width": ["get", "strokeWidth"],
          "circle-stroke-color": ["get", "strokeColor"],
        },
      });
      map.addLayer({
        id: "station-labels", type: "symbol", source: "stations", minzoom: 12.5,
        layout: {
          "text-field": ["get", "labelText"],
          "text-size": 11,
          "text-offset": [0, 1.6],
          "text-allow-overlap": false,
        },
        paint: {
          "text-color": "#cdd8f5",
          "text-halo-color": "#0a0f1e",
          "text-halo-width": 1.2,
        },
      });
      map.on("mousemove", "station-circles", e => {
        const f = e.features?.[0];
        if (!f) return;
        map.getCanvas().style.cursor = "pointer";
        const p = f.properties as Record<string, string>;
        popup
          .setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number])
          .setHTML(
            `<strong>${p.name}</strong><br/>${p.priceLabel}<br/><span class="tip-dim">${p.growthLabel}　${p.txLabel}</span>`,
          )
          .addTo(map);
      });
      map.on("mouseleave", "station-circles", () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
      });
      map.on("click", "station-circles", e => {
        const f = e.features?.[0];
        if (f) select((f.properties as { id: string }).id);
      });
      setMapReady(true);
    });
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
  }, [select]);

  // push data on lens/quarter/data change
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !stations || !quarters) return;
    const fc = buildStationFeatures(stations.stations, quarters, lensByKey(lens), quarterIdx);
    (map.getSource("stations") as maplibregl.GeoJSONSource)?.setData(fc);
  }, [mapReady, stations, quarters, lens, quarterIdx]);

  // fly to selection
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedId || !stations) return;
    const s = stations.stations.find(x => x.id === selectedId);
    if (s) map.flyTo({ center: [s.lon, s.lat], zoom: Math.max(map.getZoom(), 12.5) });
  }, [selectedId, stations]);

  return (
    <div className="map-wrap">
      <div ref={containerRef} className="map-container" />
      <LensTabs />
      <Legend />
    </div>
  );
}
```

- [ ] **Step 4: Append map styles to `web/src/styles.css`**

```css
.map-wrap, .map-container { position: absolute; inset: 0; }
.lens-tabs {
  position: absolute; top: 14px; left: 14px; z-index: 10;
  display: flex; gap: 2px; padding: 3px;
  background: rgba(13, 20, 38, 0.92); border: 1px solid var(--border); border-radius: 10px;
}
.lens-tabs button {
  background: none; border: none; color: var(--dim); font-size: 12px;
  padding: 5px 14px; border-radius: 7px; cursor: pointer;
}
.lens-tabs button.on { background: var(--accent); color: #14100a; font-weight: 600; }
.lens-tabs button.soon { color: #5a6890; cursor: default; }
.legend {
  position: absolute; left: 14px; bottom: 24px; z-index: 10;
  padding: 12px 14px; width: 230px; font-size: 11px;
}
.legend-row { color: var(--dim); margin-top: 6px; }
.legend-row.faint { color: var(--faint); font-size: 10px; }
.station-tip .maplibregl-popup-content {
  background: rgba(10, 16, 32, 0.95); color: var(--text);
  border: 1px solid var(--accent); border-radius: 8px; padding: 10px 12px; font-size: 12px;
}
.station-tip .maplibregl-popup-tip { border-top-color: var(--accent); }
.tip-dim { color: var(--dim); }
```

- [ ] **Step 5: Route it.** In `web/src/App.tsx` replace the `/` route element with `<MapScreen />` (add `import { MapScreen } from "./screens/MapScreen";`).

- [ ] **Step 6: Visual verification**

Run: `cd web && npm run dev` then open http://localhost:5173 (ensure Task 3's dev data exists).
Expected: dark Tokyo basemap; 3 fixture station circles around Nakano/Shinjuku; hover shows the tooltip with price/growth/tx; click flies in; lens tabs switch colors; legend updates; 再開発 tab disabled. Check the console for errors. If CJK labels fail to render on zoom ≥ 12.5, the Carto glyph stack is the cause — acceptable fallback is removing `text-field` CJK by setting `labelText` to price only; note whatever you did in the commit body.

- [ ] **Step 7: Build + commit**

Run: `cd web && npm test && npm run build` — Expected: green.

```bash
git add web/src
git commit -m "feat(web): map screen with lens-driven station circles, tooltip, legend"
```

---

### Task 10: Quarter time slider

**Files:**
- Create: `web/src/components/TimeSlider.tsx`
- Modify: `web/src/screens/MapScreen.tsx` (mount it)
- Test: covered by store test (lens switch resets scrub) + visual

- [ ] **Step 1: Create `web/src/components/TimeSlider.tsx`**

```tsx
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
```

- [ ] **Step 2: Styles** (append to `web/src/styles.css`)

```css
.time-slider {
  position: absolute; bottom: 24px; left: 50%; transform: translateX(-50%);
  z-index: 10; display: flex; align-items: center; gap: 10px; padding: 8px 14px;
}
.time-slider input[type="range"] { width: 280px; accent-color: var(--accent); }
.time-slider .play {
  background: none; border: 1px solid var(--border); border-radius: 6px;
  color: var(--dim); width: 28px; height: 24px; cursor: pointer; font-size: 10px;
}
.time-slider .q-label { font-size: 12px; color: var(--text); min-width: 110px; }
.time-slider .q-hint { font-size: 10px; color: var(--faint); }
.time-slider.disabled { opacity: 0.55; }
```

- [ ] **Step 3: Mount in MapScreen** — add `<TimeSlider />` next to `<Legend />` (import it).

- [ ] **Step 4: Visual verify + commit**

Run: `cd web && npm run dev` — scrub the slider on 価格 lens: circle colors/sizes change per quarter (fixture data: 中野 grows from 60万 to 66万 across 2022→2023); on other lenses the slider is disabled with the hint; play button animates and stops at latest.

```bash
git add web/src
git commit -m "feat(web): quarter time slider with playback on the price lens"
```

---

### Task 11: Station card (slide-over) with price chart

**Files:**
- Create: `web/src/components/StationCard.tsx`, `web/src/components/PriceChart.tsx`
- Modify: `web/src/screens/MapScreen.tsx` (mount card)
- Test: `web/src/components/PriceChart.test.ts` (data shaping only)

- [ ] **Step 1: Write failing test `web/src/components/PriceChart.test.ts`** (test the exported pure helper, not the component)

```ts
import { describe, expect, it } from "vitest";
import { chartRows } from "./PriceChart";

describe("chartRows", () => {
  it("merges median series with landprice by year", () => {
    const rows = chartRows(
      { quarters: ["2023Q3", "2023Q4"], median_ppsm: [500000, 660000], tx_count: [3, 5] },
      { years: [2023], price: [800000] },
    );
    expect(rows).toHaveLength(2);
    expect(rows[0]).toEqual({ q: "2023Q3", median: 500000, landprice: 800000 });
    expect(rows[1].landprice).toBeNull(); // landprice only plotted on Q3 of its year
  });
  it("handles null medians and missing landprice", () => {
    const rows = chartRows(
      { quarters: ["2023Q4"], median_ppsm: [null], tx_count: [0] },
      null,
    );
    expect(rows[0]).toEqual({ q: "2023Q4", median: null, landprice: null });
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd web && npm test` — Expected: FAIL — cannot resolve `./PriceChart`

- [ ] **Step 3: Implement `web/src/components/PriceChart.tsx`**

```tsx
import {
  Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { formatMan } from "../lib/format";
import type { StationDetail } from "../types";

export interface ChartRow {
  q: string;
  median: number | null;
  landprice: number | null;
}

/** Land price is yearly — plot it on the Q3 tick of its year (地価公示 is as of Jan 1; Q3 keeps it mid-series visually distinct). */
export function chartRows(
  series: StationDetail["series"],
  landprice: StationDetail["landprice"],
): ChartRow[] {
  const byYear = new Map<number, number>();
  landprice?.years.forEach((y, i) => byYear.set(y, landprice.price[i]));
  return series.quarters.map((q, i) => ({
    q,
    median: series.median_ppsm[i],
    landprice: q.endsWith("Q3") ? (byYear.get(Number(q.slice(0, 4))) ?? null) : null,
  }));
}

export function PriceChart({ detail }: { detail: StationDetail }) {
  const rows = chartRows(detail.series, detail.landprice);
  return (
    <div style={{ height: 150 }}>
      <ResponsiveContainer>
        <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <XAxis dataKey="q" tick={{ fontSize: 9, fill: "#7a8ab8" }} interval="preserveStartEnd" />
          <YAxis tickFormatter={v => formatMan(v as number)} tick={{ fontSize: 9, fill: "#7a8ab8" }} width={44} />
          <Tooltip
            contentStyle={{ background: "#0d1426", border: "1px solid #1a2440", fontSize: 11 }}
            formatter={(v: number) => `${formatMan(v)}円`}
          />
          <Line dataKey="median" name="㎡単価" stroke="#c9a86a" dot={false} strokeWidth={2} connectNulls />
          <Line dataKey="landprice" name="地価公示" stroke="#5f8fe0" strokeDasharray="5 4" dot={{ r: 2 }} connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 4: Implement `web/src/components/StationCard.tsx`**

```tsx
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
    setDetail("loading");
    void fetchDetail(selectedId).then(setDetail);
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
          {detail.similar.length > 0 && (
            <>
              <div className="label" style={{ marginTop: 10 }}>似てるのに安い駅</div>
              <div className="chips">
                {detail.similar
                  .filter(s => s.price_gap != null && s.price_gap < 0)
                  .slice(0, 5)
                  .map(s => (
                    <button key={s.id} className="chip" onClick={() => select(s.id)}>
                      {s.name} {formatPct(s.price_gap)}
                    </button>
                  ))}
              </div>
            </>
          )}
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
```

- [ ] **Step 5: Styles** (append to `web/src/styles.css`)

```css
.station-card {
  position: absolute; top: 14px; right: 14px; bottom: 24px; width: 380px;
  z-index: 15; padding: 18px; overflow-y: auto;
}
.station-card header { display: flex; justify-content: space-between; align-items: flex-start; }
.station-card h2 { margin: 0; font-size: 19px; }
.station-card .ward { color: var(--faint); font-size: 11px; font-weight: 400; }
.station-card .lines { color: var(--faint); font-size: 10px; margin-top: 2px; }
.tag {
  background: #3d2f10; color: var(--accent); border: 1px solid var(--accent);
  border-radius: 12px; padding: 3px 10px; font-size: 11px;
}
.station-card .close {
  background: none; border: none; color: var(--faint); font-size: 18px;
  cursor: pointer; margin-left: 8px;
}
.stat-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-top: 14px; }
.stat { background: #101a33; border-radius: 8px; padding: 8px; }
.stat-v { font-size: 15px; font-weight: 600; margin-top: 2px; }
.stat-v.good { color: var(--good); }
.stat-v.warn { color: var(--warn); }
.dim { color: var(--dim); }
.small { font-size: 12px; }
.chips { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
.chip {
  background: #101a33; border: 1px solid #2a3a60; border-radius: 12px;
  padding: 4px 10px; color: #7fd4ef; font-size: 11px; cursor: pointer;
}
.card-actions { display: flex; gap: 8px; margin-top: 16px; }
.card-actions button { flex: 1; }
```

- [ ] **Step 6: Mount** — in `MapScreen.tsx` render `<StationCard />` inside `.map-wrap` (import it).

- [ ] **Step 7: Test, visual verify, commit**

Run: `cd web && npm test && npm run dev` — chartRows tests pass; clicking a circle opens the card with stats, chart (中野 60万→66万 trend + dashed 地価公示 points), hazard text, similar chips that jump stations, both action buttons navigate.

```bash
git add web/src
git commit -m "feat(web): station card slide-over with price chart and similar stations"
```

---

### Task 12: Station search

**Files:**
- Create: `web/src/components/SearchBox.tsx`
- Modify: `web/src/App.tsx` (mount in TopBar)
- Test: `web/src/components/SearchBox.test.ts` (matching logic)

- [ ] **Step 1: Write failing test `web/src/components/SearchBox.test.ts`**

```ts
import { describe, expect, it } from "vitest";
import { matchStations } from "./SearchBox";
import type { Station } from "../types";

const st = (name: string, ward = "中野区"): Station => ({
  id: name, name, ward, lines: [], lon: 0, lat: 0, label: "標準",
  metrics: {
    median_ppsm: 1, tx_count: 1, growth_1y: null, growth_3y: null, growth_5y: null,
    volatility: null, dispersion: null, liquidity_score: 0, relative_value: null,
    hazard_score: null, pop_resilience: null, gravity: 0, confidence: 1,
  },
});

describe("matchStations", () => {
  const all = [st("中野"), st("中野坂上"), st("東中野"), st("新宿", "新宿区")];
  it("prefix matches rank before substring matches", () => {
    const r = matchStations(all, "中野").map(s => s.name);
    expect(r[0]).toBe("中野");
    expect(r).toContain("東中野");
  });
  it("matches ward names too", () => {
    expect(matchStations(all, "新宿区").map(s => s.name)).toEqual(["新宿"]);
  });
  it("empty query returns nothing", () => {
    expect(matchStations(all, "")).toEqual([]);
  });
});
```

- [ ] **Step 2: Run to verify failure** — `cd web && npm test` → FAIL.

- [ ] **Step 3: Implement `web/src/components/SearchBox.tsx`**

```tsx
import { useMemo, useState } from "react";
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
  const navigate = useNavigate();
  const hits = useMemo(() => matchStations(stations?.stations ?? [], q), [stations, q]);

  return (
    <div className="search">
      <input
        placeholder="駅名で検索…"
        value={q}
        onChange={e => setQ(e.target.value)}
        aria-label="駅名で検索"
      />
      {hits.length > 0 && (
        <ul className="search-hits panel">
          {hits.map(s => (
            <li key={s.id}>
              <button onClick={() => { select(s.id); setQ(""); navigate("/"); }}>
                {s.name} <span className="faint">{s.ward}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Styles + mount.** Append to `web/src/styles.css`:

```css
.search { position: relative; }
.search input { width: 200px; border-radius: 16px; }
.search-hits {
  position: absolute; top: 36px; right: 0; width: 240px; z-index: 30;
  list-style: none; margin: 0; padding: 4px;
}
.search-hits button {
  display: block; width: 100%; text-align: left; background: none; border: none;
  color: var(--text); padding: 7px 10px; border-radius: 6px; cursor: pointer; font-size: 13px;
}
.search-hits button:hover { background: #101a33; }
.faint { color: var(--faint); font-size: 11px; }
```

In `App.tsx`, render `<TopBar><SearchBox /></TopBar>` (only when `status === "ready"`; pass nothing otherwise).

- [ ] **Step 5: Test + commit**

Run: `cd web && npm test && npm run build` — green.

```bash
git add web/src
git commit -m "feat(web): station search with prefix-ranked matching"
```

---

### Task 13: Rail lines + hazard overlay (リスク lens)

**Files:**
- Modify: `web/src/screens/MapScreen.tsx`

- [ ] **Step 1: Add overlay loading to the map-load handler in `MapScreen.tsx`.** Inside `map.on("load", ...)`, after the station layers, add (fire-and-forget; all overlays are optional files):

```ts
const addOptionalGeojson = async (
  id: string,
  url: string,
  layer: Omit<maplibregl.LayerSpecification, "id" | "source">,
  before?: string,
) => {
  try {
    const res = await fetch(url);
    if (!res.ok) return;
    const data = (await res.json()) as GeoJSON.FeatureCollection;
    if (!map.getSource(id)) map.addSource(id, { type: "geojson", data });
    map.addLayer({ id, source: id, ...layer } as maplibregl.LayerSpecification, before);
  } catch { /* overlay is optional */ }
};

void addOptionalGeojson("rail", `${DATA_BASE}/rail.geojson`, {
  type: "line",
  paint: { "line-color": "#2e7d5b", "line-width": 1.2, "line-opacity": 0.35 },
}, "station-circles");

void addOptionalGeojson("hazard-flood", `${DATA_BASE}/hazard/flood.geojson`, {
  type: "fill",
  layout: { visibility: "none" },
  paint: { "fill-color": "#3a7da0", "fill-opacity": 0.25 },
}, "rail");

void addOptionalGeojson("hazard-landslide", `${DATA_BASE}/hazard/landslide.geojson`, {
  type: "fill",
  layout: { visibility: "none" },
  paint: { "fill-color": "#a05f3a", "fill-opacity": 0.3 },
}, "rail");
```

(Import `DATA_BASE` from `../config`. The `before: "rail"` argument only works once rail exists; since flood/landslide load after rail in sequence there is a race — make `addOptionalGeojson` calls sequential with `await` inside an async IIFE: `void (async () => { await addOptionalGeojson("rail", ...); await addOptionalGeojson("hazard-flood", ...); ... })();` — and pass `before: "station-circles"` for all three so ordering never breaks.)

- [ ] **Step 2: Toggle hazard visibility by lens.** Add an effect:

```ts
useEffect(() => {
  const map = mapRef.current;
  if (!map || !mapReady) return;
  const vis = lens === "risk" ? "visible" : "none";
  for (const id of ["hazard-flood", "hazard-landslide"]) {
    if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", vis);
  }
}, [mapReady, lens]);
```

- [ ] **Step 3: Visual verify + commit**

Run: `cd web && npm run dev` — faint green rail line visible under circles; switching to リスク lens shows the fixture flood polygon (blue fill over Nakano) and landslide patch; other lenses hide them.

```bash
git add web/src/screens/MapScreen.tsx
git commit -m "feat(web): rail underlay and lens-gated hazard overlays"
```

---

### Task 14: 比較 (Compare) screen

**Files:**
- Create: `web/src/lib/compare.ts`, `web/src/screens/CompareScreen.tsx`
- Modify: `web/src/App.tsx` (route)
- Test: `web/src/lib/compare.test.ts`

- [ ] **Step 1: Write failing tests `web/src/lib/compare.test.ts`**

```ts
import { describe, expect, it } from "vitest";
import { axesFor, percentileOf, proseFor, AXES } from "./compare";
import type { Station } from "../types";

const st = (name: string, over: Partial<Station["metrics"]> = {}): Station => ({
  id: name, name, ward: "区", lines: [], lon: 0, lat: 0, label: "標準",
  metrics: {
    median_ppsm: 500000, tx_count: 50, growth_1y: 0.02, growth_3y: null, growth_5y: null,
    volatility: 0.03, dispersion: 0.2, liquidity_score: 50, relative_value: 0,
    hazard_score: 30, pop_resilience: 50, gravity: 50, confidence: 2, ...over,
  },
});

describe("percentileOf", () => {
  it("ranks within population", () => {
    expect(percentileOf([1, 2, 3, 4], 4)).toBe(100);
    expect(percentileOf([1, 2, 3, 4], 1)).toBe(0);
    expect(percentileOf([], 1)).toBe(50);
  });
});

describe("axesFor", () => {
  const all = [st("A", { growth_1y: 0.1, hazard_score: 80 }), st("B"), st("C", { growth_1y: -0.05 })];
  it("returns six axes in spec order, 0-100, safety inverted", () => {
    const ax = axesFor(all[0], all);
    expect(ax.map(a => a.key)).toEqual(AXES.map(a => a.key));
    const safety = ax.find(a => a.key === "safety")!;
    expect(safety.value).toBeLessThan(50); // hazard 80 → low safety
    ax.forEach(a => { expect(a.value).toBeGreaterThanOrEqual(0); expect(a.value).toBeLessThanOrEqual(100); });
  });
  it("null metrics fall back to 50 and are flagged", () => {
    const s = st("N", { pop_resilience: null });
    const ax = axesFor(s, [s]);
    const pop = ax.find(a => a.key === "population")!;
    expect(pop.value).toBe(50);
    expect(pop.missing).toBe(true);
  });
});

describe("proseFor", () => {
  it("mentions dimensions with a clear gap, neutrally", () => {
    const a = st("北千住", { growth_1y: 0.12, liquidity_score: 90, hazard_score: 70 });
    const b = st("赤羽", { growth_1y: 0.02, liquidity_score: 60, hazard_score: 20 });
    const text = proseFor(a, b, [a, b]).join("");
    expect(text).toContain("北千住");
    expect(text).toContain("赤羽");
    expect(text).not.toMatch(/勝|負|対決/); // no game language
  });
});
```

- [ ] **Step 2: Run to verify failure** — `cd web && npm test` → FAIL.

- [ ] **Step 3: Implement `web/src/lib/compare.ts`**

```ts
import type { Station } from "../types";

export function percentileOf(values: number[], v: number): number {
  if (values.length === 0) return 50;
  const below = values.filter(x => x < v).length;
  const equal = values.filter(x => x === v).length;
  return (100 * (below + equal / 2)) / values.length;
}

export interface Axis {
  key: "momentum" | "value" | "liquidity" | "population" | "safety" | "gravity";
  label: string;
}

export const AXES: Axis[] = [
  { key: "momentum", label: "価格の勢い" },
  { key: "value", label: "相対バリュー" },
  { key: "liquidity", label: "流動性" },
  { key: "population", label: "人口基盤" },
  { key: "safety", label: "災害安全" },
  { key: "gravity", label: "駅引力" },
];

export interface AxisValue extends Axis {
  value: number; // 0–100, larger = better
  missing: boolean;
}

export function axesFor(s: Station, all: Station[]): AxisValue[] {
  const pop = (sel: (m: Station["metrics"]) => number | null) =>
    all.map(x => sel(x.metrics)).filter((v): v is number => v != null);

  const pct = (sel: (m: Station["metrics"]) => number | null): { value: number; missing: boolean } => {
    const v = sel(s.metrics);
    if (v == null) return { value: 50, missing: true };
    return { value: percentileOf(pop(sel), v), missing: false };
  };

  const direct = (v: number | null): { value: number; missing: boolean } =>
    v == null ? { value: 50, missing: true } : { value: v, missing: false };

  return [
    { ...AXES[0], ...pct(m => m.growth_1y) },
    { ...AXES[1], ...pct(m => m.relative_value) },
    { ...AXES[2], ...direct(s.metrics.liquidity_score) },
    { ...AXES[3], ...direct(s.metrics.pop_resilience) },
    { ...AXES[4], ...(s.metrics.hazard_score == null ? { value: 50, missing: true } : { value: 100 - s.metrics.hazard_score, missing: false }) },
    { ...AXES[5], ...direct(s.metrics.gravity) },
  ];
}

const GAP = 15; // points of axis difference worth mentioning

/** Neutral per-dimension prose. No winners, no game language. */
export function proseFor(a: Station, b: Station, all: Station[]): string[] {
  const ax = axesFor(a, all);
  const bx = axesFor(b, all);
  const aheadA: string[] = [];
  const aheadB: string[] = [];
  ax.forEach((av, i) => {
    if (av.missing || bx[i].missing) return;
    const d = av.value - bx[i].value;
    if (d >= GAP) aheadA.push(av.label);
    if (d <= -GAP) aheadB.push(av.label);
  });
  const out: string[] = [];
  if (aheadA.length) out.push(`${a.name}は${aheadA.join("・")}で上回る。`);
  if (aheadB.length) out.push(`${b.name}は${aheadB.join("・")}で優位。`);
  if (!out.length) out.push("主要観点に大きな差はない。");
  return out;
}
```

- [ ] **Step 4: Implement `web/src/screens/CompareScreen.tsx`**

```tsx
import {
  PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer,
} from "recharts";
import { axesFor, proseFor, AXES } from "../lib/compare";
import { formatMan, formatPct } from "../lib/format";
import { matchStations } from "../components/SearchBox";
import { useApp } from "../store";
import { useState } from "react";
import type { Station } from "../types";

function StationPicker({ slot, value }: { slot: 0 | 1; value: Station | null }) {
  const { stations, compare } = useApp();
  const [q, setQ] = useState("");
  const hits = matchStations(stations?.stations ?? [], q);
  const set = (id: string) => {
    const next: [string | null, string | null] = [...compare] as [string | null, string | null];
    next[slot] = id;
    useApp.setState({ compare: next });
    setQ("");
  };
  return (
    <div className="picker">
      {value ? <strong>{value.name}</strong> : <em className="faint">未選択</em>}
      <input placeholder="駅名…" value={q} onChange={e => setQ(e.target.value)} />
      {hits.length > 0 && (
        <ul className="search-hits panel">
          {hits.map(s => <li key={s.id}><button onClick={() => set(s.id)}>{s.name}</button></li>)}
        </ul>
      )}
    </div>
  );
}

const ROWS: { label: string; get: (s: Station) => string }[] = [
  { label: "㎡単価（中央値）", get: s => `${formatMan(s.metrics.median_ppsm)}円` },
  { label: "1年成長", get: s => formatPct(s.metrics.growth_1y) },
  { label: "取引数（4Q）", get: s => `${s.metrics.tx_count}件` },
  { label: "ハザード", get: s => s.metrics.hazard_score?.toFixed(0) ?? "—" },
  { label: "人口レジリエンス", get: s => s.metrics.pop_resilience != null ? `p${s.metrics.pop_resilience.toFixed(0)}` : "—" },
  { label: "ラベル", get: s => s.label },
];

export function CompareScreen() {
  const { stations, compare } = useApp();
  const all = stations?.stations ?? [];
  const a = all.find(s => s.id === compare[0]) ?? null;
  const b = all.find(s => s.id === compare[1]) ?? null;

  const radarData = AXES.map((ax, i) => ({
    axis: ax.label,
    a: a ? axesFor(a, all)[i].value : 0,
    b: b ? axesFor(b, all)[i].value : 0,
  }));

  return (
    <div className="compare">
      <div className="compare-pickers">
        <StationPicker slot={0} value={a} />
        <span className="faint">と</span>
        <StationPicker slot={1} value={b} />
      </div>

      {a && b ? (
        <div className="compare-body">
          <div className="panel" style={{ padding: 16 }}>
            <div style={{ display: "flex", justifyContent: "center", gap: 18, fontSize: 13 }}>
              <span style={{ color: "var(--accent)" }}>● {a.name}</span>
              <span style={{ color: "#6f9bd8" }}>● {b.name}</span>
            </div>
            <div style={{ height: 300 }}>
              <ResponsiveContainer>
                <RadarChart data={radarData} outerRadius="75%">
                  <PolarGrid stroke="#1e2a4a" />
                  <PolarAngleAxis dataKey="axis" tick={{ fontSize: 10, fill: "#9fb0d8" }} />
                  <Radar dataKey="a" stroke="#c9a86a" fill="#c9a86a" fillOpacity={0.18} />
                  <Radar dataKey="b" stroke="#6f9bd8" fill="#6f9bd8" fillOpacity={0.18} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div>
            <table className="compare-table panel">
              <thead>
                <tr><th /><th style={{ color: "var(--accent)" }}>{a.name}</th><th style={{ color: "#6f9bd8" }}>{b.name}</th></tr>
              </thead>
              <tbody>
                {ROWS.map(r => (
                  <tr key={r.label}><td>{r.label}</td><td>{r.get(a)}</td><td>{r.get(b)}</td></tr>
                ))}
              </tbody>
            </table>
            <div className="panel" style={{ padding: 14, marginTop: 12, fontSize: 13, lineHeight: 1.8, color: "var(--dim)" }}>
              {proseFor(a, b, all).map((line, i) => <p key={i} style={{ margin: 0 }}>{line}</p>)}
            </div>
          </div>
        </div>
      ) : (
        <p className="dim" style={{ marginTop: 24 }}>
          2つの駅を選ぶと比較が表示されます。地図の駅カードから「比較に追加」もできます。
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Styles + route.** Append to `web/src/styles.css`:

```css
.compare { padding: 20px 24px; max-width: 980px; margin: 0 auto; }
.compare-pickers { display: flex; align-items: center; gap: 14px; }
.picker { position: relative; display: flex; align-items: center; gap: 10px; }
.compare-body { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 18px; }
.compare-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.compare-table td, .compare-table th { padding: 8px 10px; border-bottom: 1px solid #131c33; text-align: right; }
.compare-table td:first-child { color: var(--dim); text-align: left; }
```

Route in `App.tsx`: `/compare` → `<CompareScreen />`.

- [ ] **Step 6: Test, visual verify, commit**

Run: `cd web && npm test && npm run dev` — compare tests pass; picking 中野 vs 高円寺 renders two translucent radar shapes, the stat table, and neutral prose with no winner language.

```bash
git add web/src
git commit -m "feat(web): compare screen with six-axis radar and neutral prose"
```

---

### Task 15: 査定 (Benchmark) screen with saved deals

**Files:**
- Create: `web/src/lib/benchmark.ts`, `web/src/lib/deals.ts`, `web/src/screens/BenchmarkScreen.tsx`
- Modify: `web/src/App.tsx` (route)
- Test: `web/src/lib/benchmark.test.ts`, `web/src/lib/deals.test.ts`

- [ ] **Step 1: Write failing tests `web/src/lib/benchmark.test.ts`**

```ts
import { describe, expect, it } from "vitest";
import { evaluateDeal, percentileFromHist } from "./benchmark";
import type { Hist, Station } from "../types";

const hist: Hist = {
  window_quarters: 8,
  bin_edges: [400000, 500000, 600000, 700000],
  counts: [10, 20, 10],
};

describe("percentileFromHist", () => {
  it("interpolates within bins", () => {
    expect(percentileFromHist(hist, 400000)).toBe(0);
    expect(percentileFromHist(hist, 700000)).toBe(100);
    expect(percentileFromHist(hist, 550000)).toBeCloseTo(50, 0); // 10 + 10 of 40
  });
  it("clamps outside range", () => {
    expect(percentileFromHist(hist, 100)).toBe(0);
    expect(percentileFromHist(hist, 9e9)).toBe(100);
  });
});

describe("evaluateDeal", () => {
  const station: Station = {
    id: "中野", name: "中野", ward: "中野区", lines: [], lon: 0, lat: 0, label: "モメンタム",
    metrics: {
      median_ppsm: 600000, tx_count: 100, growth_1y: 0.09, growth_3y: null, growth_5y: null,
      volatility: 0.03, dispersion: 0.2, liquidity_score: 30, relative_value: 0,
      hazard_score: 62, pop_resilience: 60, gravity: 70, confidence: 2,
    },
  };
  it("computes ppsm, percentile and verdict sentences", () => {
    const r = evaluateDeal({ priceYen: 27500000, sizeM2: 50, rentYenMonthly: 110000 }, station, hist);
    expect(r.ppsm).toBe(550000);
    expect(r.percentile).toBeCloseTo(50, 0);
    expect(r.grossYield).toBeCloseTo(0.048, 3);
    const text = r.verdicts.join("");
    expect(text).toContain("中央値");
    expect(text).toContain("流動性");   // liquidity 30 → thin
    expect(text).toContain("洪水");     // hazard 62 → mentioned
  });
  it("works without hist or rent", () => {
    const r = evaluateDeal({ priceYen: 30000000, sizeM2: 50 }, station, null);
    expect(r.percentile).toBeNull();
    expect(r.grossYield).toBeNull();
    expect(r.verdicts.length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 2: Write failing tests `web/src/lib/deals.test.ts`**

```ts
import { beforeEach, describe, expect, it } from "vitest";
import { listDeals, saveDeal, removeDeal, DEALS_KEY } from "./deals";

beforeEach(() => localStorage.clear());

describe("deals storage", () => {
  it("saves and lists", () => {
    saveDeal({ stationId: "中野", priceYen: 30000000, sizeM2: 50, builtYear: 2005 });
    const all = listDeals();
    expect(all).toHaveLength(1);
    expect(all[0].stationId).toBe("中野");
    expect(all[0].id).toBeTruthy();
  });
  it("removes by id", () => {
    saveDeal({ stationId: "中野", priceYen: 1, sizeM2: 1 });
    const id = listDeals()[0].id;
    removeDeal(id);
    expect(listDeals()).toHaveLength(0);
  });
  it("ignores corrupt or wrong-version storage", () => {
    localStorage.setItem(DEALS_KEY, "not json");
    expect(listDeals()).toEqual([]);
    localStorage.setItem(DEALS_KEY, JSON.stringify({ v: 99, deals: [{}] }));
    expect(listDeals()).toEqual([]);
  });
});
```

- [ ] **Step 3: Run to verify failures** — `cd web && npm test` → FAIL (both modules unresolved).

- [ ] **Step 4: Implement `web/src/lib/benchmark.ts`**

```ts
import { formatMan, formatPct } from "./format";
import type { Hist, Station } from "../types";

export function percentileFromHist(hist: Hist, ppsm: number): number {
  const { bin_edges: e, counts } = hist;
  const total = counts.reduce((a, b) => a + b, 0);
  if (total === 0) return 50;
  if (ppsm <= e[0]) return 0;
  if (ppsm >= e[e.length - 1]) return 100;
  let below = 0;
  for (let i = 0; i < counts.length; i++) {
    if (ppsm >= e[i + 1]) {
      below += counts[i];
    } else {
      below += counts[i] * ((ppsm - e[i]) / (e[i + 1] - e[i]));
      break;
    }
  }
  return (100 * below) / total;
}

export interface DealInput {
  priceYen: number;
  sizeM2: number;
  builtYear?: number;
  rentYenMonthly?: number;
}

export interface DealResult {
  ppsm: number;
  percentile: number | null;
  grossYield: number | null;
  verdicts: string[];
}

export function evaluateDeal(deal: DealInput, station: Station, hist: Hist | null): DealResult {
  const ppsm = deal.priceYen / deal.sizeM2;
  const m = station.metrics;
  const percentile = hist ? percentileFromHist(hist, ppsm) : null;
  const grossYield = deal.rentYenMonthly ? (deal.rentYenMonthly * 12) / deal.priceYen : null;

  const verdicts: string[] = [];
  if (m.median_ppsm != null) {
    const gap = ppsm / m.median_ppsm - 1;
    const dir = gap < -0.02 ? "下回る" : gap > 0.02 ? "上回る" : "ほぼ一致する";
    verdicts.push(
      `この物件の㎡単価は${formatMan(ppsm)}円。${station.name}の直近中央値（${formatMan(m.median_ppsm)}円）を${formatPct(Math.abs(gap))}${dir}。` +
      (percentile != null ? `直近2年の取引分布では下から${percentile.toFixed(0)}%の位置。` : ""),
    );
  }
  verdicts.push(
    m.liquidity_score >= 60
      ? `流動性は厚い（駅間percentile ${m.liquidity_score.toFixed(0)}）。出口は取りやすい部類。`
      : `流動性は薄い（駅間percentile ${m.liquidity_score.toFixed(0)}）。出口に時間がかかる可能性。`,
  );
  if (m.hazard_score != null) {
    verdicts.push(
      m.hazard_score > 50
        ? `洪水等のハザード負担が高め（スコア${m.hazard_score.toFixed(0)}）。保険・長期保有リスクを織り込むこと。`
        : `ハザード負担は低め（スコア${m.hazard_score.toFixed(0)}）。`,
    );
  }
  if (m.growth_1y != null) {
    verdicts.push(
      m.growth_1y > 0.03
        ? `エリアの価格モメンタムはプラス（1年${formatPct(m.growth_1y)}）。`
        : `エリアの価格モメンタムは弱い（1年${formatPct(m.growth_1y)}）。`,
    );
  }
  if (grossYield != null) {
    verdicts.push(`表面利回り ${formatPct(grossYield)}（参考値・家賃相場データなし）。`);
  }
  return { ppsm, percentile, grossYield, verdicts };
}
```

- [ ] **Step 5: Implement `web/src/lib/deals.ts`**

```ts
export const DEALS_KEY = "atlas.deals";
const VERSION = 1;

export interface SavedDeal {
  id: string;
  stationId: string;
  priceYen: number;
  sizeM2: number;
  builtYear?: number;
  rentYenMonthly?: number;
  savedAt: string;
}

interface Box { v: number; deals: SavedDeal[]; }

function read(): Box {
  try {
    const raw = localStorage.getItem(DEALS_KEY);
    if (!raw) return { v: VERSION, deals: [] };
    const box = JSON.parse(raw) as Box;
    if (box.v !== VERSION || !Array.isArray(box.deals)) return { v: VERSION, deals: [] };
    return box;
  } catch {
    return { v: VERSION, deals: [] };
  }
}

export function listDeals(): SavedDeal[] {
  return read().deals;
}

export function saveDeal(d: Omit<SavedDeal, "id" | "savedAt">): SavedDeal {
  const box = read();
  const deal: SavedDeal = {
    ...d,
    id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    savedAt: new Date().toISOString(),
  };
  box.deals.push(deal);
  localStorage.setItem(DEALS_KEY, JSON.stringify(box));
  return deal;
}

export function removeDeal(id: string): void {
  const box = read();
  box.deals = box.deals.filter(d => d.id !== id);
  localStorage.setItem(DEALS_KEY, JSON.stringify(box));
}
```

- [ ] **Step 6: Implement `web/src/screens/BenchmarkScreen.tsx`**

```tsx
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
```

- [ ] **Step 7: Styles + route.** Append to `web/src/styles.css`:

```css
.benchmark { padding: 20px 24px; max-width: 760px; margin: 0 auto; display: grid; gap: 16px; }
.bench-form { padding: 18px; }
.bench-form h3 { margin: 0 0 12px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.form-grid label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--dim); }
.bench-result { padding: 18px; }
.verdicts { margin: 12px 0 0; padding-left: 18px; line-height: 1.9; font-size: 13px; color: var(--dim); }
.bench-saved { padding: 18px; }
.bench-saved ul { list-style: none; margin: 8px 0 0; padding: 0; }
.bench-saved li { display: flex; gap: 14px; align-items: center; padding: 6px 0; border-bottom: 1px solid #131c33; font-size: 13px; }
```

Route in `App.tsx`: `/benchmark` → `<BenchmarkScreen />`.

- [ ] **Step 8: Test, visual verify, commit**

Run: `cd web && npm test && npm run dev` — benchmark + deals tests pass; entering 中野 / 2750万 / 50㎡ / 家賃11万 shows the histogram with the deal marker and verdict sentences incl. 参考値 yield; saving persists across reloads; 駅カード's この駅で査定 button pre-selects the station.

```bash
git add web/src
git commit -m "feat(web): benchmark screen with histogram positioning and saved deals"
```

---

### Task 16: Playwright smoke test + web README

**Files:**
- Create: `web/playwright.config.ts`, `web/e2e/smoke.spec.ts`, `web/README.md`
- Modify: `web/package.json` (script + devDep), `.gitignore`

- [ ] **Step 1: Install Playwright**

Run: `cd web && npm i -D @playwright/test && npx playwright install chromium`

- [ ] **Step 2: Create `web/playwright.config.ts`**

```ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  use: { baseURL: "http://localhost:4173" },
  webServer: {
    command: "npm run build && npm run preview",
    port: 4173,
    reuseExistingServer: true,
  },
});
```

- [ ] **Step 3: Create `web/e2e/smoke.spec.ts`**

```ts
import { expect, test } from "@playwright/test";

test("core loop: map → search → card → compare", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Tokyo Alpha Atlas")).toBeVisible();
  await expect(page.getByRole("link", { name: "比較" })).toBeVisible();

  // search opens the station card (DOM-driven; no canvas clicking)
  await page.getByLabel("駅名で検索").fill("中野");
  await page.getByRole("button", { name: /中野/ }).first().click();
  await expect(page.getByRole("heading", { name: /中野/ })).toBeVisible();
  await expect(page.getByText("㎡単価（中央値）")).toBeVisible();

  // add to compare and verify the radar renders
  await page.getByRole("button", { name: "比較に追加" }).click();
  await expect(page).toHaveURL(/compare/);
  await expect(page.getByText("価格の勢い")).toBeVisible();
});
```

- [ ] **Step 4: Add script + gitignore.** In `web/package.json` scripts add `"e2e": "playwright test"`. Append to `.gitignore`:

```
web/test-results/
web/playwright-report/
```

- [ ] **Step 5: Run the smoke test** (requires Task 3 dev data)

Run: `cd web && npm run e2e`
Expected: 1 passed.

- [ ] **Step 6: Create `web/README.md`**

```markdown
# Tokyo Alpha Atlas — web

Static frontend reading JSON artifacts from `public/data/` (generated by `../pipeline`).

## Develop

    cd ../pipeline && make dev-data   # fixture artifacts (3 stations) — or `make refresh` with real data
    npm install
    npm run dev                       # http://localhost:5173

## Test

    npm test      # vitest (lib logic)
    npm run e2e   # Playwright smoke (builds + previews automatically)

## Screens

- 地図 (/) — lens tabs (価格・モメンタム・割安・流動性・リスク), quarter time slider (価格 lens),
  hover tooltip, station card slide-over. Low-confidence stations render hollow gray.
- 比較 (/compare) — two stations, six-axis radar, neutral per-dimension prose.
- 査定 (/benchmark) — deal entry, position on the station's trailing-8Q price histogram,
  saved deals in localStorage.

Data freshness shows in the map legend (from `meta.json`). A schema-version mismatch
between app and data shows an explicit error screen instead of misrendering.
```

- [ ] **Step 7: Full check + commit**

Run: `cd web && npm test && npm run build && npm run e2e` — all green.

```bash
git add web/playwright.config.ts web/e2e web/README.md web/package.json web/package-lock.json .gitignore
git commit -m "test(web): playwright smoke for the core loop; web README"
```

---

## Self-review notes (done at planning time)

- **Spec §5 coverage:** map+lenses+slider+tooltip+fog (Tasks 8–10), card with 地価公示 overlay/hazard/similar/actions (Task 11), search (Task 12), rail+hazard overlays (Task 13), compare radar+prose (Task 14), benchmark histogram+localStorage (Task 15), tone rules baked into copy (no emoji, 比較 not 対決). §6: schema gate + error screen (Tasks 5,7), データ不足 card (Task 11), versioned deals storage (Task 15). §7: vitest for lens/label/verdict/percentile math (Tasks 4–8, 14–15), Playwright smoke (Task 16).
- **Accepted divergences:** age-band-adjusted benchmark percentile deferred (needs a new artifact; spec said "when n allows"); citywide `landprice.json` artifact deferred (card-level 地価公示 series ships); 再開発 lens shown as disabled tab per spec deferral; time scrub limited to 価格 lens (only per-quarter medians exist per quarter — other lenses are snapshot-only by construction); compare sparklines deferred; card label rule-on-hover deferred (pipeline doesn't emit matched rule text); saved-deal re-evaluation against refreshed data deferred (inputs persist, verdicts recomputed only on manual 査定); 地価公示 chart truncated to transaction-era x-axis (1983–2004 series emitted but not plotted — revisit with real data); e2e smoke covers the loop via search/DOM, not canvas hover.
- **Type consistency check:** `Hist`/`StationDetail.hist` (Tasks 2/4/15), `LensKey` (6/7/8), `matchStations` exported from SearchBox and reused in Compare (12/14), `DATA_BASE` (5/13) — all consistent.
- **Carto basemap + glyph risk** is called out in Task 9 with a concrete fallback.
