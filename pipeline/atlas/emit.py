import json
import re
import shutil
from pathlib import Path

import geopandas as gpd
import jsonschema
import numpy as np
import pandas as pd
from shapely.geometry import box as shapely_box

from atlas import aggregate, config, schemas, score
from atlas.config import SCHEMA_VERSION
from atlas.label import label_all
from atlas.quarters import qlabel


_UNSAFE = re.compile(r'[/\\:*?"<>|#%]')


def _safe_id(name: str) -> str:
    """Filesystem- and URL-safe station id derived from the display name."""
    return _UNSAFE.sub("_", name)


def _jsonable(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    raise TypeError(f"not jsonable: {type(x)}")


def _clean_num(v):
    if v is None or (isinstance(v, float) and np.isnan(v)) or pd.isna(v):
        return None
    return float(v)


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
        if np.ptp(vals) == 0:
            out[st] = None
            continue
        counts, edges = np.histogram(vals, bins=config.HIST_BINS)
        out[st] = {
            "window_quarters": config.HIST_WINDOW_QUARTERS,
            "bin_edges": [float(e) for e in edges],
            "counts": [int(c) for c in counts],
        }
    return out


def _dominant_ward(con):
    return dict(con.execute("""
        select station, mode(municipality) from clean_transactions group by 1
    """).fetchall())


def _display_name(record: dict) -> str:
    display = record.get("display_name")
    station = record["station"]
    return display if display == station else station


def build_docs(con, report):
    asof = aggregate.asof_qidx(con)
    snapshot = aggregate.build_price_snapshot(con, asof)
    stations_df = con.execute("select * from stations").df()
    if "display_name" not in stations_df.columns:
        stations_df["display_name"] = stations_df["name_norm"]
    scored = score.build_scores(snapshot, stations_df)
    for col in ("hazard_score", "pop_resilience", "redevelopment_score", "planning_intensity"):
        if col not in scored.columns:
            scored[col] = None
    scored = label_all(scored)
    wards = _dominant_ward(con)
    hists = _histograms(con, asof)

    # Collision guard: two distinct station names must not map to the same safe id
    seen_ids: dict[str, str] = {}
    for name in scored["station"]:
        sid = _safe_id(name)
        if sid in seen_ids and seen_ids[sid] != name:
            raise ValueError(
                f"safe_id collision: '{name}' and '{seen_ids[sid]}' "
                f"both map to id '{sid}'"
            )
        seen_ids[sid] = name

    station_entries = []
    display_by_key = {
        r["name_norm"]: (r["display_name"] if r["display_name"] == r["name_norm"] else r["name_norm"])
        for r in stations_df[["name_norm", "display_name"]].to_dict("records")
    }
    for r in scored.to_dict("records"):
        display_name = _display_name(r)
        station_entries.append({
            "id": _safe_id(r["station"]), "name": display_name,
            "ward": wards.get(r["station"], ""),
            "lines": list(r["lines"]),
            "lon": float(r["lon"]), "lat": float(r["lat"]),
            "label": r["label"],
            "metrics": {
                "median_ppsm": _clean_num(r["median_ppsm"]),
                "tx_count": int(r["tx_count"]),
                "growth_1y": _clean_num(r["growth_1y"]),
                "growth_3y": _clean_num(r["growth_3y"]),
                "growth_5y": _clean_num(r["growth_5y"]),
                "volatility": _clean_num(r["volatility"]),
                "dispersion": _clean_num(r["dispersion"]),
                "liquidity_score": float(r["liquidity_score"]),
                "relative_value": _clean_num(r.get("relative_value")),
                "hazard_score": _clean_num(r.get("hazard_score")),
                "pop_resilience": _clean_num(r.get("pop_resilience")),
                "redevelopment_score": _clean_num(r.get("redevelopment_score")),
                "planning_intensity": _clean_num(r.get("planning_intensity")),
                "gravity": float(r["gravity"]),
                "confidence": int(r["confidence"]),
            },
        })

    # Zero-window stations: present in quarterly_medians but absent from the
    # trailing-4Q snapshot (spec: never disappear — render as fog/データ薄).
    qm = aggregate.quarterly_medians(con)
    scored_names = set(scored["station"])
    historical_stations = set(qm["station"].unique())
    zero_window_names = historical_stations - scored_names
    if zero_window_names:
        st_lookup = stations_df.set_index("name_norm")
        hist_wards = dict(con.execute("""
            select station, mode(municipality) from clean_transactions group by 1
        """).fetchall())
        # Compute gravity for all stations so zero-window ones get a real value
        try:
            grav_series = score.add_gravity(
                stations_df.rename(columns={"name_norm": "station"})
            ).set_index("station")["gravity"]
        except Exception:
            grav_series = pd.Series(dtype=float)
        for name in sorted(zero_window_names):
            sid = _safe_id(name)
            if sid in seen_ids and seen_ids[sid] != name:
                raise ValueError(
                    f"safe_id collision: '{name}' and '{seen_ids[sid]}' "
                    f"both map to id '{sid}'"
                )
            seen_ids[sid] = name
            if name not in st_lookup.index:
                continue
            st = st_lookup.loc[name]
            display_value = st.get("display_name", name)
            display_name = display_value if display_value == name else name
            grav_val = float(grav_series[name]) if name in grav_series.index else 50.0
            hazard_val = _clean_num(st.get("hazard_score")) if "hazard_score" in st.index else None
            pop_res_val = _clean_num(st.get("pop_resilience")) if "pop_resilience" in st.index else None
            redevelopment_val = _clean_num(st.get("redevelopment_score")) if "redevelopment_score" in st.index else None
            planning_val = _clean_num(st.get("planning_intensity")) if "planning_intensity" in st.index else None
            station_entries.append({
                "id": sid, "name": display_name,
                "ward": hist_wards.get(name, ""),
                "lines": list(st.get("lines", [])),
                "lon": float(st["lon"]), "lat": float(st["lat"]),
                "label": "データ薄",
                "metrics": {
                    "median_ppsm": None,
                    "tx_count": 0,
                    "growth_1y": None, "growth_3y": None, "growth_5y": None,
                    "volatility": None,
                    "dispersion": None,
                    "liquidity_score": 0.0,
                    "relative_value": None,
                    "hazard_score": hazard_val,
                    "pop_resilience": pop_res_val,
                    "redevelopment_score": redevelopment_val,
                    "planning_intensity": planning_val,
                    "gravity": grav_val,
                    "confidence": 0,
                },
            })

    stations_doc = {"schema_version": SCHEMA_VERSION, "asof": qlabel(asof),
                    "stations": station_entries}

    qmin, qmax = int(qm.qidx.min()), int(qm.qidx.max())
    quarter_labels = [qlabel(i) for i in range(qmin, qmax + 1)]
    per_station = {}
    for st, g in qm.groupby("station"):
        m = [None] * len(quarter_labels)
        n = [0] * len(quarter_labels)
        for row in g.itertuples():
            pos = int(row.qidx) - qmin
            n[pos] = int(row.n)
            if row.n >= config.MIN_QUARTER_TX:
                m[pos] = float(row.med)
        per_station[_safe_id(st)] = {"m": m, "n": n}
    quarters_doc = {"schema_version": SCHEMA_VERSION, "quarters": quarter_labels,
                    "stations": per_station}

    ppsm_by_id = {e["id"]: e["metrics"]["median_ppsm"] for e in station_entries}
    detail_docs = {}
    # Build detail docs for scored stations (have full metrics + similar list)
    for r, entry in zip(scored.to_dict("records"), station_entries):
        sid = entry["id"]
        own_ppsm = entry["metrics"]["median_ppsm"]
        series = per_station.get(sid, {"m": [], "n": []})
        similar = [{"id": _safe_id(s), "name": display_by_key.get(s, s),
                    "median_ppsm": ppsm_by_id.get(_safe_id(s)),
                    "price_gap": (None if ppsm_by_id.get(_safe_id(s)) is None or own_ppsm == 0
                                  else ppsm_by_id[_safe_id(s)] / own_ppsm - 1)}
                   for s in r["similar"]]
        detail_docs[sid] = {
            "schema_version": SCHEMA_VERSION, "id": sid, "name": entry["name"],
            "series": {"quarters": quarter_labels,
                       "median_ppsm": series["m"], "tx_count": series["n"]},
            "similar": similar,
            "hazard": r.get("hazard_detail") if isinstance(r.get("hazard_detail"), dict) else None,
            "redevelopment": r.get("redevelopment_detail") if isinstance(r.get("redevelopment_detail"), dict) else None,
            "landprice": r.get("landprice_series") if isinstance(r.get("landprice_series"), dict) else None,
            "hist": hists.get(r["station"], None),
        }
    # Build detail docs for zero-window stations (full historical series, similar=[])
    for entry in station_entries[len(scored):]:
        sid = entry["id"]
        series = per_station.get(sid, {"m": [], "n": []})
        detail_docs[sid] = {
            "schema_version": SCHEMA_VERSION, "id": sid, "name": entry["name"],
            "series": {"quarters": quarter_labels,
                       "median_ppsm": series["m"], "tx_count": series["n"]},
            "similar": [],
            "hazard": None,
            "redevelopment": None,
            "landprice": None,
            "hist": hists.get(entry["id"], None),
        }

    # Enrich meta.json sources with structured objects (item 6)
    n_stations_clean = int(con.execute("select count(*) from stations").fetchone()[0])
    stations_cols = con.execute("describe stations").df()["column_name"].tolist()
    stations_table = con.execute("select * from stations").df()
    risk_scored = (
        int(stations_table["hazard_score"].notna().sum())
        if "hazard_score" in stations_cols else 0
    )
    population_scored = (
        int(stations_table["pop_change"].notna().sum())
        if "pop_change" in stations_cols else 0
    )
    redevelopment_scored = (
        int(stations_table["redevelopment_score"].notna().sum())
        if "redevelopment_score" in stations_cols else 0
    )
    has_landprice = "landprice_series" in stations_cols
    meta_doc = {
        "schema_version": SCHEMA_VERSION,
        "asof": qlabel(asof),
        "generated_rows": {k: v for k, v in report.items()},
        "sources": {
            "region": {
                "label": config.REGION_LABEL,
                "bbox": list(config.REGION_BBOX),
            },
            "transactions": {
                "label": "MLIT 不動産取引価格情報",
                "rows_clean": report.get("rows_out", report.get("rows_in")),
                "asof": qlabel(asof),
            },
            "stations": {
                "label": "国土数値情報 N02/S12",
                "count": n_stations_clean,
            },
            "risk": {
                "scored": risk_scored,
                "total": n_stations_clean,
            },
            "population": {
                "scored": population_scored,
                "total": n_stations_clean,
            },
            "redevelopment": {
                "scored": redevelopment_scored,
                "total": n_stations_clean,
            },
            "api_cache": {
                "tiles": int(report.get("_api_cache_tiles", 0) or 0),
            },
            "landprice": has_landprice,
        },
    }
    return stations_doc, quarters_doc, detail_docs, meta_doc


def emit_all(con, report, out_dir: Path | None = None,
             rail_src: Path | None = None, hazard_dir: Path | None = None,
             redevelopment_dir: Path | None = None, api_cache_tiles: int = 0):
    """Build all docs in memory, validate ALL against schemas, only then write."""
    out_dir = Path(out_dir or config.OUT_DIR)
    rail_src = Path(rail_src or config.RAW_DIR / "n02" / "rail_sections.geojson")
    hazard_dir = Path(hazard_dir or config.RAW_DIR / "hazard")
    redevelopment_dir = Path(redevelopment_dir or config.RAW_DIR / "redevelopment")
    report = {**report, "_api_cache_tiles": int(api_cache_tiles or 0)}
    stations_doc, quarters_doc, detail_docs, meta_doc = build_docs(con, report)

    jsonschema.validate(stations_doc, schemas.STATIONS_SCHEMA)
    jsonschema.validate(quarters_doc, schemas.QUARTERS_SCHEMA)
    for d in detail_docs.values():
        jsonschema.validate(d, schemas.DETAIL_SCHEMA)
    jsonschema.validate(meta_doc, schemas.META_SCHEMA)

    tmp = out_dir.parent / (out_dir.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    (tmp / "station").mkdir(parents=True)

    def dump(path, doc):
        path.write_text(json.dumps(doc, ensure_ascii=False, default=_jsonable))

    dump(tmp / "stations.json", stations_doc)
    dump(tmp / "quarters.json", quarters_doc)
    dump(tmp / "meta.json", meta_doc)
    for sid, doc in detail_docs.items():
        dump(tmp / "station" / f"{sid}.json", doc)

    if rail_src.exists():
        rail = gpd.read_file(rail_src)
        missing = {config.N02_LINE, config.N02_OPERATOR} - set(rail.columns)
        if missing:
            print(f"emit: rail_sections missing columns {missing}, skipping overlay")
        else:
            rail = rail.rename(columns={config.N02_LINE: "line", config.N02_OPERATOR: "operator"})
            # Clip rail to the current region bbox and simplify.
            lon_min, lat_min, lon_max, lat_max = config.REGION_BBOX
            bbox_geom = shapely_box(lon_min, lat_min, lon_max, lat_max)
            rail_clipped = gpd.clip(rail[["line", "operator", "geometry"]], bbox_geom)
            rail_clipped["geometry"] = rail_clipped.geometry.simplify(0.0003)
            rail_clipped.to_file(tmp / "rail.geojson", driver="GeoJSON")
    (tmp / "hazard").mkdir(exist_ok=True)
    for name in ("flood", "landslide", "liquefaction", "embankment", "danger_zone"):
        src = hazard_dir / f"{name}.geojson"
        if src.exists():
            g = gpd.read_file(src)
            g["geometry"] = g.geometry.make_valid().simplify(0.0003)
            g.to_file(tmp / "hazard" / f"{name}.geojson", driver="GeoJSON")

    (tmp / "redevelopment").mkdir(exist_ok=True)
    for name in ("district_plan", "high_utilization", "city_roads"):
        src = redevelopment_dir / f"{name}.geojson"
        if src.exists():
            g = gpd.read_file(src)
            g["geometry"] = g.geometry.make_valid().simplify(0.0003)
            g.to_file(tmp / "redevelopment" / f"{name}.geojson", driver="GeoJSON")

    old = out_dir.parent / (out_dir.name + ".old")
    if old.exists():
        shutil.rmtree(old)
    if out_dir.exists():
        out_dir.rename(old)
    tmp.rename(out_dir)
    if old.exists():
        shutil.rmtree(old)
