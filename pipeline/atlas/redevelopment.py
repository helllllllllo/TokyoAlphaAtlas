from pathlib import Path
import re

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point
from shapely.errors import GEOSException

from atlas import config


_NUM_RE = re.compile(r"\d+(?:\.\d+)?")


def _station_buffers(stations: pd.DataFrame, meters: int = 1000) -> gpd.GeoDataFrame:
    gdf = gpd.GeoDataFrame(
        stations.copy(),
        geometry=[Point(xy) for xy in zip(stations.lon, stations.lat)],
        crs=4326,
    ).to_crs(config.METRIC_CRS)
    gdf["geometry"] = gdf.geometry.buffer(meters)
    return gdf


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


def _parse_number(text: object) -> float | None:
    if text is None or pd.isna(text):
        return None
    m = _NUM_RE.search(str(text).translate(str.maketrans("０１２３４５６７８９．", "0123456789.")))
    return float(m.group(0)) if m else None


def _landprice_trend(series: object) -> float | None:
    if not isinstance(series, dict):
        return None
    prices = series.get("price") or []
    if len(prices) < 2:
        return None
    first = float(prices[0])
    last = float(prices[-1])
    return (last / first - 1) if first > 0 else None


def _trend_signal(value: float | None, low: float, high: float) -> float:
    if value is None or pd.isna(value):
        return 50.0
    return float(np.clip((value - low) / (high - low), 0, 1) * 100)


def _zoning_intensity(use_area: object, floor_ratio: float | None) -> float:
    far_score = 0.0 if floor_ratio is None else float(np.clip(floor_ratio / 800, 0, 1) * 70)
    use = "" if use_area is None or pd.isna(use_area) else str(use_area)
    if "商業" in use:
        bonus = 30.0
    elif "近隣" in use or "準工業" in use:
        bonus = 20.0
    elif "住居" in use:
        bonus = 12.0
    else:
        bonus = 5.0
    return float(np.clip(far_score + bonus, 0, 100))


def _dominant_zoning(zoning: gpd.GeoDataFrame | None, buf) -> tuple[dict | None, float]:
    if zoning is None:
        return None, 0.0
    cand = zoning.sindex.query(buf, predicate="intersects")
    if len(cand) == 0:
        return None, 0.0
    sub = zoning.iloc[cand]
    try:
        areas = sub.geometry.intersection(buf).area
    except GEOSException:
        areas = pd.Series(1.0, index=sub.index)
    if areas.empty or float(areas.max()) <= 0:
        return None, 0.0
    row = sub.loc[areas.idxmax()]
    far = _parse_number(row.get("u_floor_area_ratio_ja"))
    coverage = _parse_number(row.get("u_building_coverage_ratio_ja"))
    intensity = _zoning_intensity(row.get("use_area_ja"), far)
    return {
        "use_area": None if pd.isna(row.get("use_area_ja")) else row.get("use_area_ja"),
        "floor_area_ratio": far,
        "building_coverage_ratio": coverage,
        "intensity": round(intensity, 1),
    }, intensity


def _polygon_summary(layer: gpd.GeoDataFrame | None, buf, name_cols: tuple[str, ...]) -> tuple[dict, float]:
    if layer is None:
        return {"count": None, "coverage": None, "names": []}, 0.0
    cand = layer.sindex.query(buf, predicate="intersects")
    if len(cand) == 0:
        return {"count": 0, "coverage": 0.0, "names": []}, 0.0
    sub = layer.iloc[cand]
    try:
        inter = sub.geometry.intersection(buf)
        coverage = min(float(inter.area.sum()) / float(buf.area), 1.0)
    except GEOSException:
        coverage = 1.0
    names = []
    for col in name_cols:
        if col in sub.columns:
            names.extend([str(v) for v in sub[col].dropna().unique() if str(v)])
    signal = min(100.0, 45.0 + coverage * 55.0)
    return {
        "count": int(len(sub)),
        "coverage": round(coverage, 3),
        "names": sorted(set(names))[:5],
    }, signal


def _line_summary(layer: gpd.GeoDataFrame | None, buf, name_cols: tuple[str, ...]) -> tuple[dict, float]:
    if layer is None:
        return {"count": None, "names": []}, 0.0
    cand = layer.sindex.query(buf, predicate="intersects")
    if len(cand) == 0:
        return {"count": 0, "names": []}, 0.0
    sub = layer.iloc[cand]
    names = []
    for col in name_cols:
        if col in sub.columns:
            names.extend([str(v) for v in sub[col].dropna().unique() if str(v)])
    signal = min(100.0, 35.0 + len(sub) * 20.0)
    return {
        "count": int(len(sub)),
        "names": sorted(set(names))[:5],
    }, signal


def add_redevelopment(stations: pd.DataFrame, src_dir: Path | None = None) -> pd.DataFrame:
    src = Path(src_dir or config.RAW_DIR / "redevelopment")
    out = stations.copy()
    zoning = _read_layer(src / "zoning.geojson")
    district = _read_layer(src / "district_plan.geojson")
    high = _read_layer(src / "high_utilization.geojson")
    roads = _read_layer(src / "city_roads.geojson")

    if all(layer is None for layer in (zoning, district, high, roads)):
        out["redevelopment_score"] = np.nan
        out["planning_intensity"] = np.nan
        out["redevelopment_detail"] = None
        return out

    buffers = _station_buffers(stations)
    scores, intensities, details = [], [], []
    for i, st in buffers.iterrows():
        zoning_detail, zoning_signal = _dominant_zoning(zoning, st.geometry)
        district_detail, district_signal = _polygon_summary(
            district, st.geometry, ("plan_name", "district_name", "plan_type_ja")
        )
        high_detail, high_signal = _polygon_summary(
            high, st.geometry, ("advanced_name", "advanced_type_ja")
        )
        road_detail, road_signal = _line_summary(
            roads, st.geometry, ("planning_road_ja", "route_name", "decision_date")
        )
        planning = (
            zoning_signal * 0.40
            + district_signal * 0.20
            + high_signal * 0.25
            + road_signal * 0.15
        )

        lp_trend = _landprice_trend(out.at[i, "landprice_series"] if "landprice_series" in out else None)
        pop_trend = out.at[i, "pop_change"] if "pop_change" in out else None
        land_signal = _trend_signal(lp_trend, -0.10, 0.25)
        pop_signal = _trend_signal(pop_trend, -0.25, 0.25)
        score = planning * 0.75 + land_signal * 0.15 + pop_signal * 0.10

        scores.append(round(float(score), 1))
        intensities.append(round(float(planning), 1))
        details.append({
            "score": round(float(score), 1),
            "projects_proxy": int(
                (district_detail["count"] or 0)
                + (high_detail["count"] or 0)
                + (road_detail["count"] or 0)
            ),
            "zoning": zoning_detail,
            "district_plan": district_detail,
            "high_utilization": high_detail,
            "city_roads": road_detail,
            "landprice_trend": None if lp_trend is None else round(float(lp_trend), 4),
            "population_trend": None if pop_trend is None or pd.isna(pop_trend) else round(float(pop_trend), 4),
        })

    out["redevelopment_score"] = scores
    out["planning_intensity"] = intensities
    out["redevelopment_detail"] = details
    return out
