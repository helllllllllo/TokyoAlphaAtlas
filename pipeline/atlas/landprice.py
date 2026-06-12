import re
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from atlas import config

MAX_DIST_M = 1000
_YEAR_RE = re.compile(r"L01-(\d{4})")


def add_landprice(stations: pd.DataFrame, src_dir: Path | None = None) -> pd.DataFrame:
    """For each station: yearly official land price of the nearest 地価公示
    point within MAX_DIST_M, as {'years': [...], 'price': [...]} or None."""
    src_dir = Path(src_dir or config.RAW_DIR / "landprice")
    out = stations.copy()
    files = sorted(src_dir.glob("L01-*.geojson")) if src_dir.exists() else []
    if not files:
        out["landprice_series"] = None
        return out

    pts = gpd.GeoDataFrame(
        stations[[]].copy(),
        geometry=[Point(xy) for xy in zip(stations.lon, stations.lat)],
        crs=4326,
    ).to_crs(config.METRIC_CRS).reset_index(drop=True)

    per_station: list[dict] = [dict() for _ in range(len(stations))]
    for f in files:
        m = _YEAR_RE.search(f.name)
        if m is None:
            continue
        year = int(m.group(1))
        lp = gpd.read_file(f).to_crs(config.METRIC_CRS)
        joined = gpd.sjoin_nearest(pts, lp[[config.LANDPRICE_PRICE_ATTR, "geometry"]],
                                   how="left", max_distance=MAX_DIST_M,
                                   distance_col="_d")
        # equidistant ties duplicate rows — keep the first match per station
        joined = joined[~joined.index.duplicated(keep="first")]
        prices = joined[config.LANDPRICE_PRICE_ATTR]
        for i in range(len(stations)):
            price = prices.iloc[i]
            if pd.notna(price):
                per_station[i][year] = float(price)

    series = []
    for rec in per_station:
        if not rec:
            series.append(None)
        else:
            years = sorted(rec)
            series.append({"years": years, "price": [rec[y] for y in years]})
    out["landprice_series"] = series
    return out
