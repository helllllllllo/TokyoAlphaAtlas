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
        stations.copy(),
        geometry=[Point(xy) for xy in zip(stations.lon, stations.lat)],
        crs=4326,
    ).to_crs(config.METRIC_CRS)

    per_station: list[dict] = [dict() for _ in range(len(stations))]
    for f in files:
        year = int(_YEAR_RE.search(f.name).group(1))
        lp = gpd.read_file(f).to_crs(config.METRIC_CRS)
        for i, st in enumerate(pts.geometry):
            d = lp.geometry.distance(st)
            j = d.idxmin()
            if d.loc[j] <= MAX_DIST_M:
                per_station[i][year] = float(lp.loc[j, config.LANDPRICE_PRICE_ATTR])

    series = []
    for rec in per_station:
        if not rec:
            series.append(None)
        else:
            years = sorted(rec)
            series.append({"years": years, "price": [rec[y] for y in years]})
    out["landprice_series"] = series
    return out
