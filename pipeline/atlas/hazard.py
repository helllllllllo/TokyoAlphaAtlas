from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from atlas import config


def _station_buffers(stations: pd.DataFrame, meters: int) -> gpd.GeoDataFrame:
    g = gpd.GeoDataFrame(
        stations.copy(),
        geometry=[Point(xy) for xy in zip(stations.lon, stations.lat)],
        crs=4326,
    ).to_crs(config.METRIC_CRS)
    g["geometry"] = g.geometry.buffer(meters)
    return g


def add_hazard(stations: pd.DataFrame,
               flood_path: Path | None = None,
               landslide_path: Path | None = None,
               liquefaction_path: Path | None = None) -> pd.DataFrame:
    """Adds hazard_score (0–100 or NaN) and hazard_detail (dict or None).
    Missing source files degrade gracefully: absent components are dropped
    from the weighting; if ALL sources are missing, hazard is NaN/None."""
    flood_path = Path(flood_path or config.RAW_DIR / "hazard" / "flood.geojson")
    landslide_path = Path(landslide_path or config.RAW_DIR / "hazard" / "landslide.geojson")
    liq_path = Path(liquefaction_path or config.RAW_DIR / "hazard" / "liquefaction.geojson")

    out = stations.copy()
    buffers = _station_buffers(stations, config.STATION_BUFFER_M)
    buf_area = buffers.geometry.area

    flood_frac = None
    if flood_path.exists():
        flood = gpd.read_file(flood_path).to_crs(config.METRIC_CRS)
        flood["w"] = flood[config.FLOOD_RANK_ATTR].map(
            lambda r: config.FLOOD_DEPTH_WEIGHTS.get(int(r), 1.0) if pd.notna(r) else 0.5)
        fracs = []
        for i, buf in buffers.iterrows():
            inter = flood.geometry.intersection(buf.geometry)
            weighted = float((inter.area * flood.w).sum())
            fracs.append(min(weighted / buf_area.loc[i], 1.0))
        flood_frac = pd.Series(fracs, index=buffers.index)

    slide_flag = None
    if landslide_path.exists():
        slide = gpd.read_file(landslide_path).to_crs(config.METRIC_CRS)
        slide_flag = buffers.geometry.apply(lambda b: bool(slide.intersects(b).any()))

    liq_frac = None
    if liq_path.exists():
        liq = gpd.read_file(liq_path).to_crs(config.METRIC_CRS)
        liq_frac = buffers.geometry.apply(
            lambda b: min(float(liq.geometry.intersection(b).area.sum()) / b.area, 1.0))

    components = {"flood": flood_frac,
                  "landslide": None if slide_flag is None else slide_flag.astype(float),
                  "liquefaction": liq_frac}
    available = {k: v for k, v in components.items() if v is not None}

    if not available:
        out["hazard_score"] = np.nan
        out["hazard_detail"] = None
        return out

    total_w = sum(config.HAZARD_WEIGHTS[k] for k in available)
    raw = sum(config.HAZARD_WEIGHTS[k] * v for k, v in available.items())
    out["hazard_score"] = (100 * raw / total_w).values
    details = []
    for i in buffers.index:
        details.append({
            "flood": None if flood_frac is None else round(float(flood_frac.loc[i]), 3),
            "landslide": None if slide_flag is None else bool(slide_flag.loc[i]),
            "liquefaction": None if liq_frac is None else round(float(liq_frac.loc[i]), 3),
        })
    out["hazard_detail"] = details
    return out
