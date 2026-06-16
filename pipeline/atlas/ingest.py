from pathlib import Path
import gzip
import json
import math
import time
import urllib.parse
import urllib.request

import geopandas as gpd
import pandas as pd

from atlas import config
from atlas.quarters import qindex, qlabel
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

# Columns to materialise from raw CSVs; price_type default logic still works
# when "価格情報区分" is absent because usecols only keeps present columns.
_KEEP = set(TX_COLUMNS) | {"価格情報区分", "station_lon", "station_lat"}
_RAW_COLUMNS = [
    "property_type", "municipality", "district", "station_name",
    "station_minutes", "price_total", "area_sqm", "built_text",
    "period_text", "price_type", "station_lon", "station_lat",
]
_XPT001_BASE_URL = "https://www.reinfolib.mlit.go.jp/ex-api/external/XPT001"
_ZEN2HAN = str.maketrans("０１２３４５６７８９．，", "0123456789.,")


def read_csv_any(path: Path) -> pd.DataFrame:
    for enc in ("cp932", "utf-8-sig"):
        try:
            return pd.read_csv(path, encoding=enc, dtype=str,
                               usecols=lambda c: c in _KEEP)
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
        out = df[list(keep)].rename(columns=keep)
        out["station_lon"] = None
        out["station_lat"] = None
        frames.append(out[_RAW_COLUMNS])
    if not frames:
        raise FileNotFoundError(f"no CSVs in {src_dir}")
    all_df = pd.concat(frames, ignore_index=True)
    con.register("_tx", all_df)
    con.execute("create or replace table raw_transactions as select * from _tx")
    con.unregister("_tx")
    return len(all_df)


def _ascii_num(text: object) -> str:
    if text is None:
        return ""
    return str(text).translate(_ZEN2HAN).replace(",", "").strip()


def _parse_japanese_yen(text: object) -> str:
    value = _ascii_num(text)
    if not value:
        return ""
    total = 0.0
    if "億" in value:
        head, tail = value.split("億", 1)
        try:
            total += float(head) * 100_000_000
        except ValueError:
            pass
        value = tail
    if "万" in value:
        head = value.split("万", 1)[0].replace("円", "")
        try:
            total += float(head) * 10_000
        except ValueError:
            pass
    elif total == 0:
        digits = "".join(ch for ch in value if ch.isdigit() or ch == ".")
        if digits:
            total = float(digits)
    return str(int(round(total))) if total else ""


def _parse_area_sqm(text: object) -> str:
    value = _ascii_num(text)
    digits = []
    for ch in value:
        if ch.isdigit() or ch == ".":
            digits.append(ch)
        elif digits:
            break
    return "".join(digits)


def api_period(q: str) -> str:
    """Convert '2025Q2' to XPT/XIT period syntax '20252'."""
    return f"{q[:4]}{q[5]}"


def _period_chunks(from_period: str, to_period: str, chunk_quarters: int) -> list[tuple[str, str]]:
    start = qindex(from_period)
    end = qindex(to_period)
    if start > end:
        raise ValueError(f"from_period {from_period} after to_period {to_period}")
    out = []
    cur = start
    while cur <= end:
        chunk_end = min(cur + chunk_quarters - 1, end)
        out.append((qlabel(cur), qlabel(chunk_end)))
        cur = chunk_end + 1
    return out


def lonlat_to_tile(lon: float, lat: float, z: int) -> tuple[int, int]:
    lat_rad = math.radians(lat)
    n = 1 << z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def tiles_for_bbox(bbox: tuple[float, float, float, float] = config.REGION_BBOX,
                   z: int = config.API_TILE_ZOOM) -> list[tuple[int, int, int]]:
    lon_min, lat_min, lon_max, lat_max = bbox
    x0, y0 = lonlat_to_tile(lon_min, lat_max, z)
    x1, y1 = lonlat_to_tile(lon_max, lat_min, z)
    return [
        (z, x, y)
        for x in range(min(x0, x1), max(x0, x1) + 1)
        for y in range(min(y0, y1), max(y0, y1) + 1)
    ]


def _xpt001_cache_path(cache_dir: Path, z: int, x: int, y: int, from_period: str,
                       to_period: str, price_classification: str | None,
                       land_type_code: str) -> Path:
    pc = price_classification or "all"
    return cache_dir / (
        f"xpt001-z{z}-x{x}-y{y}-from{api_period(from_period)}-to{api_period(to_period)}"
        f"-pc{pc}-land{land_type_code}.geojson"
    )


def fetch_xpt001_tile(
    *,
    api_key: str,
    cache_dir: Path,
    z: int,
    x: int,
    y: int,
    from_period: str,
    to_period: str,
    price_classification: str | None = None,
    land_type_code: str = "07",
    force: bool = False,
    timeout: int = config.API_TIMEOUT_SECONDS,
) -> dict:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = _xpt001_cache_path(cache_dir, z, x, y, from_period, to_period,
                                   price_classification, land_type_code)
    if cache_path.exists() and not force:
        return json.loads(cache_path.read_text(encoding="utf-8"))

    params = {
        "response_format": "geojson",
        "z": str(z),
        "x": str(x),
        "y": str(y),
        "from": api_period(from_period),
        "to": api_period(to_period),
        "landTypeCode": land_type_code,
    }
    if price_classification:
        params["priceClassification"] = price_classification
    url = f"{_XPT001_BASE_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Ocp-Apim-Subscription-Key": api_key})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        data = res.read()
        if "gzip" in (res.headers.get("Content-Encoding") or "").lower():
            data = gzip.decompress(data)
    cache_path.write_bytes(data)
    return json.loads(data)


def xpt001_feature_to_transaction_row(feature: dict) -> dict[str, str | None]:
    props = feature.get("properties") or {}
    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates") if geom.get("type") == "Point" else None
    lon = coords[0] if isinstance(coords, list) and len(coords) >= 2 else None
    lat = coords[1] if isinstance(coords, list) and len(coords) >= 2 else None
    return {
        "property_type": props.get("land_type_name_ja") or "",
        "municipality": props.get("city_name_ja") or "",
        "district": props.get("district_name_ja") or "",
        "station_name": "",
        "station_minutes": None,
        "price_total": _parse_japanese_yen(props.get("u_transaction_price_total_ja")),
        "area_sqm": _parse_area_sqm(props.get("u_area_ja")),
        "built_text": props.get("u_construction_year_ja") or "",
        "period_text": props.get("point_in_time_name_ja") or "",
        "price_type": props.get("price_information_category_name_ja") or "",
        "station_lon": None if lon is None else str(lon),
        "station_lat": None if lat is None else str(lat),
    }


def ingest_transactions_api(
    con,
    *,
    from_period: str = config.API_DEFAULT_FROM,
    to_period: str,
    cache_dir: Path | None = None,
    tiles: list[tuple[int, int, int]] | None = None,
    api_key: str | None = None,
    price_classification: str | None = None,
    land_type_code: str = "07",
    chunk_quarters: int = 4,
    throttle_seconds: float = config.API_THROTTLE_SECONDS,
    force: bool = False,
) -> int:
    key = api_key or config.get_mlit_api_key()
    if not key:
        raise RuntimeError("MLIT API key is not configured")
    cache = Path(cache_dir or config.API_CACHE_DIR)
    tile_list = tiles or tiles_for_bbox()
    rows = []
    for chunk_from, chunk_to in _period_chunks(from_period, to_period, chunk_quarters):
        for z, x, y in tile_list:
            cache_path = _xpt001_cache_path(
                cache, z, x, y, chunk_from, chunk_to, price_classification, land_type_code
            )
            was_cached = cache_path.exists() and not force
            doc = fetch_xpt001_tile(
                api_key=key,
                cache_dir=cache,
                z=z, x=x, y=y,
                from_period=chunk_from,
                to_period=chunk_to,
                price_classification=price_classification,
                land_type_code=land_type_code,
                force=force,
            )
            for feature in doc.get("features", []):
                rows.append(xpt001_feature_to_transaction_row(feature))
            if throttle_seconds > 0 and not was_cached:
                time.sleep(throttle_seconds)
    if not rows:
        raise FileNotFoundError("no XPT001 features fetched")
    all_df = pd.DataFrame(rows, columns=_RAW_COLUMNS).drop_duplicates().reset_index(drop=True)
    con.register("_tx", all_df)
    con.execute("create or replace table raw_transactions as select * from _tx")
    con.unregister("_tx")
    return len(all_df)


def _in_bbox(lon, lat, bbox=None) -> "pd.Series":
    """Return boolean mask: True for points inside the bounding box."""
    if bbox is None:
        bbox = config.REGION_BBOX
    lon_min, lat_min, lon_max, lat_max = bbox
    return (lon >= lon_min) & (lon <= lon_max) & (lat >= lat_min) & (lat <= lat_max)


def _homonym_clusters(group: pd.DataFrame, lon_col: str, lat_col: str) -> pd.Series:
    """Cluster same-name station geometries by distance so homonyms survive."""
    from atlas.score import haversine_km

    idx = list(group.index)
    parent = {i: i for i in idx}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for pos, a in enumerate(idx):
        for b in idx[pos + 1:]:
            dist = haversine_km(
                float(group.at[a, lon_col]),
                float(group.at[a, lat_col]),
                float(group.at[b, lon_col]),
                float(group.at[b, lat_col]),
            )
            if dist <= config.SAME_NAME_MERGE_RADIUS_KM:
                union(a, b)

    root_to_label = {}
    labels = []
    for i in idx:
        root = find(i)
        if root not in root_to_label:
            root_to_label[root] = len(root_to_label)
        labels.append(root_to_label[root])
    return pd.Series(labels, index=idx)


def _line_hint(lines: pd.Series) -> str:
    vals = sorted({str(v) for v in lines.dropna() if str(v)})
    return vals[0] if vals else "駅"


def _assign_station_keys(df: pd.DataFrame) -> pd.DataFrame:
    """Assign unique station keys while preserving readable base names."""
    if df.empty:
        return df.assign(base_name_norm=[], station_key=[], display_name=[])

    pieces = []
    for base, group in df.groupby("name_norm", sort=False):
        g = group.copy()
        g["base_name_norm"] = base
        g["_cluster"] = _homonym_clusters(g, "lon", "lat")
        cluster_count = int(g["_cluster"].nunique())
        key_by_cluster: dict[int, str] = {}
        used: set[str] = set()
        for cluster, cg in g.groupby("_cluster", sort=True):
            if cluster_count == 1:
                key = base
            else:
                key = f"{base}（{_line_hint(cg['line'])}）"
                if key in used:
                    lon = float(cg["lon"].mean())
                    lat = float(cg["lat"].mean())
                    key = f"{base}（{lon:.3f},{lat:.3f}）"
            used.add(key)
            key_by_cluster[int(cluster)] = key
        g["station_key"] = g["_cluster"].map(key_by_cluster)
        g["display_name"] = g["station_key"]
        pieces.append(g.drop(columns=["_cluster"]))
    return pd.concat(pieces, ignore_index=True)


def _assign_ridership_keys(rid: pd.DataFrame, stations: pd.DataFrame) -> pd.Series:
    """Map S12 ridership points to the nearest station cluster with the same base name."""
    from atlas.score import haversine_km

    by_base = {
        base: g[["name_norm", "lon", "lat"]].reset_index(drop=True)
        for base, g in stations.groupby("base_name_norm")
    }
    out = []
    for idx, row in rid.iterrows():
        candidates = by_base.get(row["name_norm"])
        if candidates is None or candidates.empty:
            out.append("")
            continue
        if len(candidates) == 1:
            out.append(str(candidates.name_norm.iloc[0]))
            continue
        dist = haversine_km(
                candidates.lon.astype(float),
                candidates.lat.astype(float),
                float(row["_lon"]),
                float(row["_lat"]),
            )
        out.append(str(candidates.name_norm.iloc[int(dist.argmin())]))
    return pd.Series(out, index=rid.index)


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
    # Clip to the region bbox BEFORE groupby to prevent same-name national stations
    # (e.g. 神田/大手町/住吉) from merging across Japan and producing sea-coords
    # or inflated ridership from non-Tokyo entries.
    df = df[_in_bbox(df["lon"], df["lat"])]
    df = _assign_station_keys(df)
    stations = df.groupby(["station_key", "base_name_norm", "display_name"]).agg(
        lon=("lon", "mean"),
        lat=("lat", "mean"),
        lines=("line", lambda s: sorted(set(s))),
        n_lines=("line", "nunique"),
        n_operators=("operator", "nunique"),
    ).reset_index().rename(columns={"station_key": "name_norm"})

    stations["ridership"] = None
    s12_file = s12_path or config.RAW_DIR / "s12" / "ridership.geojson"
    if Path(s12_file).exists():
        s12 = gpd.read_file(s12_file)
        s12_rep = s12.geometry.representative_point()
        rid = pd.DataFrame({
            "name_norm": s12[config.S12_STATION_NAME].map(normalize),
            "ridership": pd.to_numeric(s12[config.S12_RIDERSHIP], errors="coerce"),
            "_lon": s12_rep.x.values,
            "_lat": s12_rep.y.values,
        })
        # Clip S12 to bbox BEFORE summing ridership to match the N02 clip.
        rid = rid[_in_bbox(rid["_lon"], rid["_lat"])]
        rid["station_key"] = _assign_ridership_keys(rid, stations)
        rid = rid[rid["station_key"] != ""]
        rid["name_norm"] = rid["station_key"]
        rid = rid.drop(columns=["_lon", "_lat"])
        rid = rid.groupby("name_norm").ridership.sum().reset_index()
        stations = stations.drop(columns=["ridership"]).merge(rid, on="name_norm", how="left")

    con.register("_st", stations)
    con.execute("create or replace table stations as select * from _st")
    con.unregister("_st")
    return len(stations)
