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


def _read_layer(path: Path) -> gpd.GeoDataFrame | None:
    if not path.exists():
        return None
    gdf = gpd.read_file(path)
    if gdf.empty:
        return None
    gdf["geometry"] = gdf.geometry.make_valid()
    gdf = gdf.to_crs(config.METRIC_CRS)
    gdf["geometry"] = gdf.geometry.make_valid()
    return gdf


def _first_column(gdf: gpd.GeoDataFrame, names: tuple[str, ...]) -> str | None:
    for name in names:
        if name in gdf.columns:
            return name
    return None


def _coverage_fraction(layer: gpd.GeoDataFrame, buffers: gpd.GeoDataFrame,
                       buf_area: pd.Series) -> pd.Series:
    tree = layer.sindex
    fracs = []
    for i, buf in buffers.iterrows():
        cand = tree.query(buf.geometry, predicate="intersects")
        if len(cand) == 0:
            fracs.append(0.0)
            continue
        inter = layer.iloc[cand].geometry.intersection(buf.geometry)
        fracs.append(min(float(inter.area.sum()) / buf_area.loc[i], 1.0))
    return pd.Series(fracs, index=buffers.index)


def _intersects_flag(layer: gpd.GeoDataFrame, buffers: gpd.GeoDataFrame) -> pd.Series:
    tree = layer.sindex
    flags = []
    for _, buf in buffers.iterrows():
        cand = tree.query(buf.geometry, predicate="intersects")
        flags.append(len(cand) > 0)
    return pd.Series(flags, index=buffers.index)


def add_hazard(stations: pd.DataFrame,
               flood_path: Path | None = None,
               landslide_path: Path | None = None,
               liquefaction_path: Path | None = None,
               embankment_path: Path | None = None,
               danger_zone_path: Path | None = None) -> pd.DataFrame:
    """Adds hazard_score (0–100 or NaN) and hazard_detail (dict or None).
    Missing source files degrade gracefully: absent components are dropped
    from the weighting; if ALL sources are missing, hazard is NaN/None."""
    flood_path = Path(flood_path or config.RAW_DIR / "hazard" / "flood.geojson")
    landslide_path = Path(landslide_path or config.RAW_DIR / "hazard" / "landslide.geojson")
    liq_path = Path(liquefaction_path or config.RAW_DIR / "hazard" / "liquefaction.geojson")
    embankment_path = Path(embankment_path or config.RAW_DIR / "hazard" / "embankment.geojson")
    danger_zone_path = Path(danger_zone_path or config.RAW_DIR / "hazard" / "danger_zone.geojson")

    out = stations.copy()
    buffers = _station_buffers(stations, config.STATION_BUFFER_M)
    buf_area = buffers.geometry.area

    flood_frac = None
    flood = _read_layer(flood_path)
    if flood is not None:
        rank_attr = _first_column(flood, config.FLOOD_RANK_ATTR_FALLBACKS)
        if rank_attr is None:
            flood["w"] = 0.5
        else:
            flood["w"] = flood[rank_attr].map(
                lambda r: config.FLOOD_DEPTH_WEIGHTS.get(int(float(r)), 1.0) if pd.notna(r) else 0.5)
        tree = flood.sindex
        fracs = []
        for i, buf in buffers.iterrows():
            cand = tree.query(buf.geometry, predicate="intersects")
            sub = flood.iloc[cand]
            if len(sub) == 0:
                fracs.append(0.0)
                continue
            if rank_attr != config.FLOOD_RANK_ATTR:
                fracs.append(float(sub.w.max()))
                continue
            inter = sub.geometry.intersection(buf.geometry)
            weighted = float((inter.area * sub.w).sum())
            fracs.append(min(weighted / buf_area.loc[i], 1.0))
        flood_frac = pd.Series(fracs, index=buffers.index)

    slide_flag = None
    slide = _read_layer(landslide_path)
    if slide is not None:
        tree = slide.sindex
        flags = []
        for i, buf in buffers.iterrows():
            cand = tree.query(buf.geometry, predicate="intersects")
            flags.append(len(cand) > 0)
        slide_flag = pd.Series(flags, index=buffers.index)

    liq_frac = None
    liq = _read_layer(liq_path)
    if liq is not None:
        level_attr = _first_column(liq, ("liquefaction_tendency_level", "液状化発生傾向"))
        if level_attr is not None:
            liq["_w"] = pd.to_numeric(liq[level_attr], errors="coerce").fillna(0).clip(0, 5) / 5
        else:
            liq["_w"] = 1.0
        tree = liq.sindex
        fracs = []
        for i, buf in buffers.iterrows():
            cand = tree.query(buf.geometry, predicate="intersects")
            if len(cand) == 0:
                fracs.append(0.0)
                continue
            sub = liq.iloc[cand]
            if level_attr is not None:
                fracs.append(float(sub["_w"].max()))
                continue
            inter = sub.geometry.intersection(buf.geometry)
            weighted = float((inter.area * sub["_w"]).sum())
            fracs.append(min(weighted / buf_area.loc[i], 1.0))
        liq_frac = pd.Series(fracs, index=buffers.index)

    embankment_frac = None
    embankment = _read_layer(embankment_path)
    if embankment is not None:
        embankment_frac = _intersects_flag(embankment, buffers).astype(float)

    danger_flag = None
    danger = _read_layer(danger_zone_path)
    if danger is not None:
        danger_flag = _intersects_flag(danger, buffers)

    components = {"flood": flood_frac,
                  "landslide": None if slide_flag is None else slide_flag.astype(float),
                  "liquefaction": liq_frac,
                  "embankment": embankment_frac,
                  "danger_zone": None if danger_flag is None else danger_flag.astype(float)}
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
            "embankment": None if embankment_frac is None else round(float(embankment_frac.loc[i]), 3),
            "danger_zone": None if danger_flag is None else bool(danger_flag.loc[i]),
        })
    out["hazard_detail"] = details
    return out
