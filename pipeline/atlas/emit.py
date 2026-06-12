import json
import re
import shutil
from pathlib import Path

import geopandas as gpd
import jsonschema
import numpy as np
import pandas as pd

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


def _dominant_ward(con):
    return dict(con.execute("""
        select station, mode(municipality) from clean_transactions group by 1
    """).fetchall())


def build_docs(con, report):
    asof = aggregate.asof_qidx(con)
    snapshot = aggregate.build_price_snapshot(con, asof)
    stations_df = con.execute("select * from stations").df()
    scored = score.build_scores(snapshot, stations_df)
    for col in ("hazard_score", "pop_resilience"):
        if col not in scored.columns:
            scored[col] = None
    scored = label_all(scored)
    wards = _dominant_ward(con)

    station_entries = []
    for r in scored.to_dict("records"):
        station_entries.append({
            "id": _safe_id(r["station"]), "name": r["station"],
            "ward": wards.get(r["station"], ""),
            "lines": list(r["lines"]),
            "lon": float(r["lon"]), "lat": float(r["lat"]),
            "label": r["label"],
            "metrics": {
                "median_ppsm": float(r["median_ppsm"]),
                "tx_count": int(r["tx_count"]),
                "growth_1y": _clean_num(r["growth_1y"]),
                "growth_3y": _clean_num(r["growth_3y"]),
                "growth_5y": _clean_num(r["growth_5y"]),
                "volatility": _clean_num(r["volatility"]),
                "dispersion": _clean_num(r["dispersion"]),
                "liquidity_score": float(r["liquidity_score"]),
                "relative_value": _clean_num(r["relative_value"]),
                "hazard_score": _clean_num(r.get("hazard_score")),
                "pop_resilience": _clean_num(r.get("pop_resilience")),
                "gravity": float(r["gravity"]),
                "confidence": int(r["confidence"]),
            },
        })
    stations_doc = {"schema_version": SCHEMA_VERSION, "asof": qlabel(asof),
                    "stations": station_entries}

    qm = aggregate.quarterly_medians(con)
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
    for r, entry in zip(scored.to_dict("records"), station_entries):
        sid = entry["id"]
        own_ppsm = entry["metrics"]["median_ppsm"]
        series = per_station.get(sid, {"m": [], "n": []})
        similar = [{"id": _safe_id(s), "name": s,
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
            "landprice": r.get("landprice_series") if isinstance(r.get("landprice_series"), dict) else None,
        }

    meta_doc = {"schema_version": SCHEMA_VERSION, "asof": qlabel(asof),
                "generated_rows": {k: v for k, v in report.items()},
                "sources": {"transactions": "MLIT 不動産取引価格情報",
                            "stations": "国土数値情報 N02/S12"}}
    return stations_doc, quarters_doc, detail_docs, meta_doc


def emit_all(con, report, out_dir: Path | None = None,
             rail_src: Path | None = None, hazard_dir: Path | None = None):
    """Build all docs in memory, validate ALL against schemas, only then write."""
    out_dir = Path(out_dir or config.OUT_DIR)
    rail_src = Path(rail_src or config.RAW_DIR / "n02" / "rail_sections.geojson")
    hazard_dir = Path(hazard_dir or config.RAW_DIR / "hazard")
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
            rail[["line", "operator", "geometry"]].to_file(tmp / "rail.geojson", driver="GeoJSON")
    (tmp / "hazard").mkdir(exist_ok=True)
    for name in ("flood", "landslide"):
        src = hazard_dir / f"{name}.geojson"
        if src.exists():
            g = gpd.read_file(src)
            g["geometry"] = g.geometry.make_valid().simplify(0.0003)
            g.to_file(tmp / "hazard" / f"{name}.geojson", driver="GeoJSON")

    old = out_dir.parent / (out_dir.name + ".old")
    if old.exists():
        shutil.rmtree(old)
    if out_dir.exists():
        out_dir.rename(old)
    tmp.rename(out_dir)
    if old.exists():
        shutil.rmtree(old)
