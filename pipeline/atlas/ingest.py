from pathlib import Path

import geopandas as gpd
import pandas as pd

from atlas import config
from atlas.station_names import normalize

TX_COLUMNS = {
    "種類": "property_type",
    "市区町村名": "municipality",
    "地区名": "district",
    "最寄駅：名称": "station_name",
    "最寄駅：距離（分）": "station_minutes",
    "取引価格（総額）": "price_total",
    "面積（㎡）": "area_sqm",
    "建築年": "built_text",
    "取引時期": "period_text",
}


def read_csv_any(path: Path) -> pd.DataFrame:
    for enc in ("cp932", "utf-8-sig"):
        try:
            return pd.read_csv(path, encoding=enc, dtype=str)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"cannot decode {path}")


def ingest_transactions(con, src_dir: Path | None = None) -> int:
    src_dir = src_dir or config.RAW_DIR / "transactions"
    frames = []
    for p in sorted(src_dir.glob("*.csv")):
        df = read_csv_any(p)
        if "価格情報区分" not in df.columns:
            df["価格情報区分"] = "取引価格情報"
        keep = {**TX_COLUMNS, "価格情報区分": "price_type"}
        missing = [c for c in keep if c not in df.columns]
        if missing:
            raise ValueError(f"{p.name}: missing columns {missing}")
        frames.append(df[list(keep)].rename(columns=keep))
    if not frames:
        raise FileNotFoundError(f"no CSVs in {src_dir}")
    all_df = pd.concat(frames, ignore_index=True)
    con.register("_tx", all_df)
    con.execute("create or replace table raw_transactions as select * from _tx")
    con.unregister("_tx")
    return len(all_df)


def ingest_stations(con, n02_path: Path | None = None,
                    s12_path: Path | None = None) -> int:
    gdf = gpd.read_file(n02_path or config.RAW_DIR / "n02" / "stations.geojson")
    pts = gdf.geometry.representative_point()
    df = pd.DataFrame({
        "name_norm": gdf[config.N02_STATION_NAME].map(normalize),
        "line": gdf[config.N02_LINE],
        "operator": gdf[config.N02_OPERATOR],
        "lon": pts.x,
        "lat": pts.y,
    })
    df = df[df.name_norm != ""]  # nameless features would become a phantom "" station key
    stations = df.groupby("name_norm").agg(
        lon=("lon", "mean"),
        lat=("lat", "mean"),
        lines=("line", lambda s: sorted(set(s))),
        n_lines=("line", "nunique"),
        n_operators=("operator", "nunique"),
    ).reset_index()

    stations["ridership"] = None
    s12_file = s12_path or config.RAW_DIR / "s12" / "ridership.geojson"
    if Path(s12_file).exists():
        s12 = gpd.read_file(s12_file)
        rid = pd.DataFrame({
            "name_norm": s12[config.S12_STATION_NAME].map(normalize),
            "ridership": pd.to_numeric(s12[config.S12_RIDERSHIP], errors="coerce"),
        }).groupby("name_norm").ridership.sum().reset_index()
        stations = stations.drop(columns=["ridership"]).merge(rid, on="name_norm", how="left")

    con.register("_st", stations)
    con.execute("create or replace table stations as select * from _st")
    con.unregister("_st")
    return len(stations)
