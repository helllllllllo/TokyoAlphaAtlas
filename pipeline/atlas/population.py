from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from atlas import config


def add_population(stations: pd.DataFrame, mesh_path: Path | None = None) -> pd.DataFrame:
    """Adds pop_change (projected base→future, area-weighted over mesh cells
    intersecting the 1km buffer) and pop_density (people/km² in buffer)."""
    mesh_path = Path(mesh_path or config.RAW_DIR / "population" / "mesh.geojson")
    out = stations.copy()
    if not mesh_path.exists():
        out["pop_change"] = np.nan
        out["pop_density"] = np.nan
        return out

    mesh = gpd.read_file(mesh_path).to_crs(config.METRIC_CRS)
    mesh["base"] = pd.to_numeric(mesh[config.POP_BASE_ATTR], errors="coerce")
    mesh["future"] = pd.to_numeric(mesh[config.POP_FUTURE_ATTR], errors="coerce")
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
