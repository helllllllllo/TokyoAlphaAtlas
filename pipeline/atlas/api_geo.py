from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import gzip
import json
import re
import time
import urllib.parse
import urllib.request

import geopandas as gpd
import pandas as pd

from atlas import config, ingest


BASE_URL = "https://www.reinfolib.mlit.go.jp/ex-api/external"

RISK_APIS = {
    "flood": "XKT026",
    "landslide": "XKT029",
    "liquefaction": "XKT025",
    "embankment": "XKT020",
    "danger_zone": "XKT016",
}

REDEVELOPMENT_APIS = {
    "zoning": "XKT002",
    "location_optimization": "XKT003",
    "district_plan": "XKT023",
    "high_utilization": "XKT024",
    "city_roads": "XKT030",
}

API_DEFAULT_ZOOMS = {
    "XKT026": 14,
    "XPT002": 13,
}

_PARAM_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class ApiGeoSources:
    hazard_dir: Path
    population_path: Path
    landprice_dir: Path
    redevelopment_dir: Path
    overlay_hazard_dir: Path
    overlay_redevelopment_dir: Path
    tiles_fetched: int = 0


def _param_suffix(params: dict[str, object] | None) -> str:
    if not params:
        return ""
    parts = []
    for key, value in sorted(params.items()):
        safe_key = _PARAM_SAFE.sub("_", str(key))
        safe_value = _PARAM_SAFE.sub("_", str(value))
        parts.append(f"{safe_key}{safe_value}")
    return "-" + "-".join(parts)


def tile_cache_path(
    cache_dir: Path,
    api_id: str,
    z: int,
    x: int,
    y: int,
    params: dict[str, object] | None = None,
) -> Path:
    api = api_id.lower()
    return Path(cache_dir) / api / f"{api}-z{z}-x{x}-y{y}{_param_suffix(params)}.geojson"


def _normalise_doc(doc: object) -> dict:
    if isinstance(doc, dict) and doc.get("type") == "FeatureCollection":
        return doc
    if isinstance(doc, dict) and "features" in doc:
        return {"type": "FeatureCollection", "features": doc.get("features") or []}
    if isinstance(doc, list):
        return {"type": "FeatureCollection", "features": doc}
    return {"type": "FeatureCollection", "features": []}


def fetch_mlit_tile(
    api_id: str,
    *,
    z: int,
    x: int,
    y: int,
    cache_dir: Path | None = None,
    api_key: str | None = None,
    params: dict[str, object] | None = None,
    force: bool = False,
    timeout: int = config.API_TIMEOUT_SECONDS,
) -> dict:
    cache = Path(cache_dir or config.API_GEO_CACHE_DIR)
    path = tile_cache_path(cache, api_id, z, x, y, params=params)
    if path.exists() and not force:
        return json.loads(path.read_text(encoding="utf-8"))
    if not api_key:
        raise RuntimeError("MLIT API key is not configured")

    query = {"response_format": "geojson", "z": z, "x": x, "y": y}
    if params:
        query.update(params)
    url = f"{BASE_URL}/{api_id}?{urllib.parse.urlencode(query)}"
    req = urllib.request.Request(url, headers={"Ocp-Apim-Subscription-Key": api_key})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        data = res.read()
        if "gzip" in (res.headers.get("Content-Encoding") or "").lower():
            data = gzip.decompress(data)

    text = data.decode("utf-8") if isinstance(data, bytes) else str(data)
    doc = _normalise_doc(json.loads(text) if text.strip() else {})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return doc


def _feature_key(feature: dict) -> str:
    return json.dumps(feature, sort_keys=True, ensure_ascii=False, default=str)


def load_api_layer(
    api_id: str,
    *,
    cache_dir: Path | None = None,
    tiles: list[tuple[int, int, int]] | None = None,
    api_key: str | None = None,
    bbox: tuple[float, float, float, float] = config.REGION_BBOX,
    z: int | None = None,
    params: dict[str, object] | None = None,
    force: bool = False,
    throttle_seconds: float = config.API_THROTTLE_SECONDS,
) -> tuple[gpd.GeoDataFrame, int]:
    key = api_key or config.get_mlit_api_key()
    zoom = z or API_DEFAULT_ZOOMS.get(api_id, config.API_TILE_ZOOM)
    tile_list = tiles or ingest.tiles_for_bbox(bbox=bbox, z=zoom)
    cache = Path(cache_dir or config.API_GEO_CACHE_DIR)
    features: list[dict] = []
    seen: set[str] = set()

    for tile_z, x, y in tile_list:
        path = tile_cache_path(cache, api_id, tile_z, x, y, params=params)
        was_cached = path.exists() and not force
        doc = fetch_mlit_tile(
            api_id,
            z=tile_z,
            x=x,
            y=y,
            cache_dir=cache,
            api_key=key,
            params=params,
            force=force,
        )
        for feature in doc.get("features", []):
            if not feature.get("geometry"):
                continue
            key_text = _feature_key(feature)
            if key_text in seen:
                continue
            seen.add(key_text)
            features.append(feature)
        if throttle_seconds > 0 and not was_cached:
            time.sleep(throttle_seconds)

    if not features:
        return gpd.GeoDataFrame(geometry=[], crs=4326), len(tile_list)
    return gpd.GeoDataFrame.from_features(features, crs=4326), len(tile_list)


def _write_geojson(gdf: gpd.GeoDataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if gdf.empty:
        path.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")
        return
    gdf.to_file(path, driver="GeoJSON")


def _merge_year_layers(layers: list[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
    nonempty = [g for g in layers if not g.empty]
    if not nonempty:
        return gpd.GeoDataFrame(geometry=[], crs=4326)
    return gpd.GeoDataFrame(
        data=pd.concat(nonempty, ignore_index=True),
        geometry="geometry",
        crs=nonempty[0].crs,
    )


def _default_landprice_years(today: date | None = None) -> list[int]:
    year = (today or date.today()).year - 1
    return list(range(year - 3, year + 1))


def prepare_api_geo_sources(
    *,
    cache_dir: Path | None = None,
    out_dir: Path | None = None,
    bbox: tuple[float, float, float, float] = config.REGION_BBOX,
    api_key: str | None = None,
    force: bool = False,
    default_zoom: int | None = None,
    landprice_years: list[int] | None = None,
    throttle_seconds: float = config.API_THROTTLE_SECONDS,
) -> ApiGeoSources:
    key = api_key or config.get_mlit_api_key()
    if not key:
        raise RuntimeError("MLIT API key is not configured")
    cache = Path(cache_dir or config.API_GEO_CACHE_DIR)
    out = Path(out_dir or config.API_GEO_LAYER_DIR)
    zoom = default_zoom or config.API_TILE_ZOOM
    tiles_total = 0

    hazard_dir = out / "hazard"
    for name, api_id in RISK_APIS.items():
        api_zoom = API_DEFAULT_ZOOMS.get(api_id, zoom)
        gdf, n_tiles = load_api_layer(
            api_id,
            cache_dir=cache,
            bbox=bbox,
            z=api_zoom,
            api_key=key,
            force=force,
            throttle_seconds=throttle_seconds,
        )
        tiles_total += n_tiles
        _write_geojson(gdf, hazard_dir / f"{name}.geojson")

    population_dir = out / "population"
    population_path = population_dir / "mesh.geojson"
    gdf, n_tiles = load_api_layer(
        "XKT013",
        cache_dir=cache,
        bbox=bbox,
        z=zoom,
        api_key=key,
        force=force,
        throttle_seconds=throttle_seconds,
    )
    tiles_total += n_tiles
    _write_geojson(gdf, population_path)

    landprice_dir = out / "landprice"
    land_layers = []
    for year in landprice_years or _default_landprice_years():
        gdf, n_tiles = load_api_layer(
            "XPT002",
            cache_dir=cache,
            bbox=bbox,
            z=API_DEFAULT_ZOOMS["XPT002"],
            params={"year": year},
            api_key=key,
            force=force,
            throttle_seconds=throttle_seconds,
        )
        tiles_total += n_tiles
        land_layers.append(gdf)
    _write_geojson(_merge_year_layers(land_layers), landprice_dir / "XPT002.geojson")

    redevelopment_dir = out / "redevelopment"
    for name, api_id in REDEVELOPMENT_APIS.items():
        gdf, n_tiles = load_api_layer(
            api_id,
            cache_dir=cache,
            bbox=bbox,
            z=zoom,
            api_key=key,
            force=force,
            throttle_seconds=throttle_seconds,
        )
        tiles_total += n_tiles
        _write_geojson(gdf, redevelopment_dir / f"{name}.geojson")

    return ApiGeoSources(
        hazard_dir=hazard_dir,
        population_path=population_path,
        landprice_dir=landprice_dir,
        redevelopment_dir=redevelopment_dir,
        overlay_hazard_dir=hazard_dir,
        overlay_redevelopment_dir=redevelopment_dir,
        tiles_fetched=tiles_total,
    )
