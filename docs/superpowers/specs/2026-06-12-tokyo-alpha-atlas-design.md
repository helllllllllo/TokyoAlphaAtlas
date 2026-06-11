# Tokyo Alpha Atlas — MVP Design

**Date:** 2026-06-12
**Status:** Approved design, pending implementation plan
**One-liner:** A station-level real-estate micro-market explorer for Tokyo's 23 wards — find interesting areas and generate investment hypotheses, not appraise exact properties.

## 1. Goals and non-goals

**Goals**

- Let an investor explore station-area price signals on a real map of Tokyo: current levels, change over time, liquidity, hazard, and demographics.
- Surface "interesting" stations via transparent, rule-based scoring and labels.
- Compare two stations side by side (neutral analysis, no winner/loser framing).
- Benchmark a manually entered deal against its station's actual transaction distribution.
- Be a real personal tool first; demo-grade visual quality second.

**Non-goals (v1)**

- Exact property valuation or hedonic pricing models.
- Rent benchmarks (no rent dataset in scope; user-entered rent yields a 参考値 gross yield only).
- 再開発 (redevelopment) lens — deferred; needs 都市計画決定情報 integration.
- Multi-user accounts, server infrastructure, mobile-first design (mobile should be usable, not optimized).
- 3D visualization. Explicitly rejected during design: looks impressive but reads worse than 2D color.

**Key decisions made during design**

| Decision | Choice |
|---|---|
| Purpose | Personal tool first, public demo later |
| Architecture | Static precompute: Python ETL → static JSON → static frontend, no server |
| Map visual | 2D circles on a dark MapLibre basemap (3D columns rejected) |
| UI language | Japanese |
| Tone | Refined analyst tool (Bloomberg × premium fintech), not gamified. 「比較」not 「対決」, no emoji chips, no winner verdicts |
| Data access | Bulk CSV downloads now; MLIT 不動産情報ライブラリ API key being applied for, slots in later |
| Scope | All four screens in v1 |

## 2. System architecture

```
sources (MLIT bulk CSV, 国土数値情報, 東京都OD)
   │  manual quarterly run: `make refresh`
   ▼
pipeline/  (Python, uv)               ── working store: data/atlas.duckdb
   ingest → normalize → aggregate → score → label → emit
   ▼
web/public/data/  (static JSON/GeoJSON artifacts, schema-validated)
   ▼
web/  (Vite + React + TS + MapLibre GL)  ── no backend; deals in localStorage
```

**Repository layout**

```
realEstate/
├── pipeline/              # Python ETL (uv-managed)
│   ├── atlas/             # ingest/ normalize/ aggregate/ score/ label/ emit/
│   ├── tests/             # pytest with golden fixtures
│   └── data/              # raw/ downloads (gitignored) + atlas.duckdb (gitignored)
├── web/                   # Vite + React + TypeScript
│   ├── public/data/       # emitted artifacts (committed, they are small)
│   └── src/               # screens/ components/ lib/
└── docs/superpowers/specs/
```

Rationale: quarterly-updated data needs no server. DuckDB as the ETL working store keeps a future DuckDB-WASM (in-browser SQL) migration open without rework.

## 3. Data sources

| Source | Content | Access | Cadence |
|---|---|---|---|
| 不動産取引価格情報 (MLIT) | Transaction price, area, 建築年, structure, floor plan, 最寄駅名称/距離, quarter. 2005Q3+ | Bulk CSV download (no key). Later: 不動産情報ライブラリ XPT001 API | Quarterly |
| 成約価格情報 | Contract prices, 2021Q1+ | **Requires API key — deferred until key arrives.** Schema reserves `priceType` field | Quarterly |
| 地価公示 / 地価調査 | Official land prices, 1983+ | 国土数値情報 L01/L02 | Yearly |
| Rail & stations | Station points, line geometry | 国土数値情報 N02 | Static |
| Ridership | 駅別乗降客数 | 国土数値情報 S12 | Yearly |
| Flood hazard | 洪水浸水想定区域 (depth bands) | 国土数値情報 A31 | Static |
| Landslide | 土砂災害警戒区域 | 国土数値情報 A33 | Static |
| Liquefaction | 液状化リスク | 東京都 open data (best-effort; if unobtainable, hazard score covers flood+landslide only and the card marks liquefaction 「データなし」) | Static |
| Future population | 将来推計人口 1kmメッシュ (~2050) | 国土数値情報 | Static |

Property scope: **中古マンション equivalent (区分所有) only, Tokyo 23 wards.**
Important known property of the transaction data: points are located at the *nearest station*, not the property — which is exactly why this is a station-area tool. Spatial filter: 最寄駅距離 ≤ 15分.

## 4. Pipeline stages

1. **ingest** — download/refresh raw files, decode Shift-JIS, load into DuckDB raw tables. Idempotent; raw files cached on disk.
2. **normalize** —
   - 和暦 → 西暦 for 建築年 (explicit era tables; unparseable rows counted, reported, excluded — never guessed).
   - Station-name normalization: free-text 最寄駅名称 joined to N02 station geometry via normalizer (ヶ/ケ, full/half-width, parenthetical suffixes) + maintained alias table. **Pipeline fails loudly if match rate < 97%**, printing unmatched names.
   - price_per_sqm = 取引価格総額 / 面積; rows trimmed by robust MAD filter per station.
   - Stations sharing a name across lines are merged into one logical station (matching how transaction data references them); lines listed on the card.
3. **aggregate** — station × quarter: median price/m², transaction count, IQR. "Current" snapshot values use a **trailing 4-quarter window, valid when n ≥ 10** (tunable constants in one config module).
4. **score** — per station (snapshot + full quarterly series where meaningful):
   | Metric | Definition |
   |---|---|
   | median_ppsm | trailing-4Q median ¥/m² |
   | growth_1y / 3y / 5y | trailing-4Q median vs the same window 1/3/5 years earlier |
   | volatility | stddev of QoQ log-changes of quarterly median, trailing 12Q |
   | dispersion | IQR ÷ median, trailing 4Q |
   | liquidity_score | percentile rank (0–100) of trailing-4Q transaction count across stations |
   | relative_value | (cohort median − own median) ÷ cohort median, cohort = its similar stations; positive = cheaper than peers |
   | hazard_score | 0–100, weighted: depth-weighted share of 800m buffer in flood zones + landslide zone presence + liquefaction class |
   | pop_resilience | percentile of projected population change 2025→2045 in 1km mesh cells within 1km |
   | gravity | percentile of log(乗降客数) + line/operator count |
   | confidence | from transaction counts; drives muted/hollow rendering on the map |
   Similar stations: k-NN (k≈8) on **non-price** features (gravity, straight-line distance to Tokyo Station, surrounding-mesh population density, line count; z-scored) so 「似てるのに安い駅」 is same-character-lower-price, not a price-bucket tautology.
5. **label** — rule-based, priority-ordered, thresholds as named constants; the matched rule is shown on the card (transparent, no black box):
   モメンタム (growth_1y ≥ p75 ∧ liquidity ≥ p50) → 割安 (relative_value high ∧ hazard ≤ median) → 訳あり安値 (cheap vs peers ∧ (hazard high ∨ resilience low)) → 安定コア (low vol ∧ high liquidity ∧ high gravity) → プレミアム (price ≥ p90 ∧ growth > 0) → データ薄 (low confidence) → 標準.
6. **emit** — write artifacts to a temp dir, validate against JSON Schemas, then atomically swap into `web/public/data/`:
   - `stations.json` — all stations: id, name, ward, lines, lat/lng, current snapshot of all metrics, label. (Map + search.)
   - `quarters.json` — compact per-quarter series for the map time slider: for each station, [median_ppsm, tx_count] per quarter. (~600 stations × ~85 quarters, packed arrays.)
   - `station/{id}.json` — full detail: quarterly series of all metrics, 地価公示 nearest-point yearly series (1983+), hazard breakdown, similar-stations list with price gaps.
   - `rail.geojson` — line geometry, colored by operator/line.
   - `hazard/flood.geojson`, `hazard/landslide.geojson` — simplified polygons for the リスク lens overlay.
   - `landprice.json` — citywide 地価公示 context series.
   - `meta.json` — data vintage per source, row counts, schema version.

## 5. Frontend

**Stack:** Vite + React + TypeScript, MapLibre GL JS (native circle/fill/line layers — no deck.gl), Zustand for state, Recharts for charts, React Router. Static build, deployable to any static host.

**Navigation:** one top bar — 地図 / 比較 / 査定 + station search box. Station card is a slide-over panel on the map, not a separate page.

### 画面1: 地図 (/) — default screen

- Dark-styled real Tokyo basemap (OpenFreeMap vector tiles restyled to the app palette; swap to self-hosted PMTiles if external dependency becomes annoying). Pan/zoom; streets visible at high zoom.
- **Each station = a circle: color = current lens metric, radius = transaction volume, hollow gray = low confidence (データ薄).** Station name + price label appear by zoom level.
- Lens tabs (quiet text tabs): 価格 (default, blue→warm color scale) / モメンタム / 割安 / 流動性 / リスク. リスク lens additionally overlays flood/landslide polygons translucently. (再開発 deferred.)
- **Quarter time slider** (bottom): scrub 2005Q3→present; circles recolor/resize per quarter from `quarters.json`. Subtle play button for animation.
- Rail lines drawn faintly; hover any circle → tooltip (station, ¥/m², 1Y growth, tx count); click → card slides in.
- Legend (bottom-left): encoding + data vintage from `meta.json`.

### 画面2: 駅カード (slide-over on map)

Header (station, ward, lines, label tag — understated, with rule shown on hover). Six key stats (median ¥/m², 1Y growth, 3/5Y growth, tx count, hazard, pop resilience). Price time-series chart 2005→now with 地価公示 dashed long-term overlay (1983+). Hazard breakdown (flood depth / landslide / liquefaction). 「似てるのに安い駅」 chips (click → jump to that station). Actions: 比較に追加 / この駅で査定.

### 画面3: 比較 (/compare)

Two stations chosen via search or card button. 6-axis radar — 価格の勢い・相対バリュー・流動性・人口基盤・災害安全 (hazard inverted so larger = better)・駅引力 — overlaid translucently. Stat comparison table + sparklines. **Neutral per-dimension prose, no winner:** e.g. 「北千住は価格の勢いと流動性で上回る一方、洪水リスクが顕著に高い。」

### 画面4: 査定 (/benchmark)

Form: price, station (autocomplete), size m², 築年, expected rent (optional). Property type fixed 中古マンション. Result: deal's ¥/m² drawn as a marker on the station's actual trailing-8Q price histogram, percentile stated; age-band-adjusted percentile when n allows; verdict sentences covering price position, liquidity thinness, hazard, momentum; gross yield from entered rent **labeled 参考値（家賃相場データなし）**. Deals saved to localStorage (schema-versioned), listed and re-evaluated on data refresh.

**Tone rules (apply everywhere):** Japanese UI; no emoji chips; no game language (対決/勝敗/バッジ禁止); playfulness expressed through craft — smooth transitions when switching lenses or scrubbing time, careful palette, micro-animations. Reference: Bloomberg terminal × premium fintech.

## 6. Error handling & data quality

- Station-name join below 97% → hard failure with unmatched-name report; fix by extending alias table.
- Era conversion failures counted and reported per run; rows excluded.
- Artifacts schema-validated before atomic swap — a broken run cannot half-overwrite good data.
- Frontend: schema-version mismatch between app and `meta.json` → explicit error screen, not silent misrender. Thin-data stations render hollow-gray, never disappear. Missing station detail file → 「データ不足」 card. localStorage deals migrate by schema version.
- Each ETL run prints a summary (rows in/out per stage, match rates, quarters covered) for eyeball verification.

## 7. Testing

- **pipeline (pytest):** golden-fixture end-to-end test — small hand-crafted CSV with known expected medians/growth/labels must reproduce exact metrics. Unit tests: era conversion, station-name normalization, MAD trimming, each score formula, label rules.
- **web (vitest):** unit tests for lens→color mapping, label/verdict text generation, benchmark percentile math (pure TS modules, no map needed).
- **smoke (Playwright):** load map → hover tooltip → click station → card opens → add to 比較 → compare renders.

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Station-name matching messier than expected | Hard 97% gate + alias table; worst case, per-ward manual aliases (~600 stations is hand-fixable) |
| CSV format drift across years (column renames) | ingest has per-vintage column maps; golden fixtures catch breakage |
| Liquefaction data unobtainable in convenient form | Hazard score degrades gracefully to flood+landslide; card says データなし |
| Quarterly thin data at minor stations | Trailing windows + confidence rendering; never hide, always mark |
| API key never arrives | Tool fully functional on bulk CSV; contract prices are additive |

## 9. Build order (high level — detail goes in the implementation plan)

1. Pipeline skeleton + ingest/normalize for transaction CSV (the riskiest join, done first).
2. Aggregate + score + emit `stations.json` / `quarters.json` / `station/{id}.json`.
3. Map screen with 価格 lens + tooltip + card with chart.
4. Remaining lenses, hazard/population/gravity scores, labels, time slider.
5. 比較 and 査定 screens.
6. 地価公示 overlay, polish pass (motion, palette), Playwright smoke.
