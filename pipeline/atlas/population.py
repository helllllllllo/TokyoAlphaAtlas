from pathlib import Path
import re

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from atlas import config

_PTN_RE = re.compile(r"^PTN_(\d{4})$")


def _population_columns(mesh: gpd.GeoDataFrame) -> tuple[str | None, str | None]:
    if config.POP_BASE_ATTR in mesh.columns and config.POP_FUTURE_ATTR in mesh.columns:
        return config.POP_BASE_ATTR, config.POP_FUTURE_ATTR
    years = []
    for col in mesh.columns:
        m = _PTN_RE.match(str(col))
        if m:
            years.append((int(m.group(1)), col))
    if len(years) < 2:
        return None, None
    years.sort()
    return years[0][1], years[-1][1]


def add_population(stations: pd.DataFrame, mesh_path: Path | None = None) -> pd.DataFrame:
    """Adds pop_change (projected base→future, area-weighted over mesh cells
    intersecting the 1km buffer) and pop_density (people/km² in buffer)."""
    mesh_path = Path(mesh_path or config.RAW_DIR / "population" / "mesh.geojson")
    out = stations.copy()
    if not mesh_path.exists():
        out["pop_change"] = np.nan
        out["pop_density"] = np.nan
        return out

    mesh = gpd.read_file(mesh_path)
    if mesh.empty:
        out["pop_change"] = np.nan
        out["pop_density"] = np.nan
        return out
    base_attr, future_attr = _population_columns(mesh)
    if base_attr is None or future_attr is None:
        out["pop_change"] = np.nan
        out["pop_density"] = np.nan
        return out
    mesh = mesh.to_crs(config.METRIC_CRS)
    mesh["base"] = pd.to_numeric(mesh[base_attr], errors="coerce")
    mesh["future"] = pd.to_numeric(mesh[future_attr], errors="coerce")
    mesh["cell_area"] = mesh.geometry.area

    pts = gpd.GeoDataFrame(
        stations.copy(),
        geometry=[Point(xy) for xy in zip(stations.lon, stations.lat)],
        crs=4326,
    ).to_crs(config.METRIC_CRS)
    pts["geometry"] = pts.geometry.buffer(config.POP_BUFFER_M)

    tree = mesh.sindex
    changes, densities = [], []
    for _, st in pts.iterrows():
        cand = tree.query(st.geometry, predicate="intersects")
        sub = mesh.iloc[cand]
        inter = sub.geometry.intersection(st.geometry)
        w = inter.area
        sel = w > 0
        if not sel.any():
            changes.append(np.nan)
            densities.append(np.nan)
            continue
        frac = (w[sel] / sub.cell_area[sel])
        base = float((sub.base[sel] * frac).sum())
        future = float((sub.future[sel] * frac).sum())
        changes.append(future / base - 1 if base > 0 else np.nan)
        densities.append(base / (st.geometry.area / 1e6))
    out["pop_change"] = changes
    out["pop_density"] = densities
    return out
