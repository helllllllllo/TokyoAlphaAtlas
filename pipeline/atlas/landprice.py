import re
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from atlas import config

MAX_DIST_M = 1000
_YEAR_RE = re.compile(r"L01-(\d{4})")
_ERA_RE = re.compile(r"(令和|平成)(\d+|元)年?")
_DIGIT_RE = re.compile(r"\d[\d,]*")


def _parse_api_year(text: object) -> int | None:
    if text is None or pd.isna(text):
        return None
    value = str(text).translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    m = _ERA_RE.search(value)
    if m:
        n = 1 if m.group(2) == "元" else int(m.group(2))
        return (2018 + n) if m.group(1) == "令和" else (1988 + n)
    m = re.search(r"(20\d{2}|19\d{2})", value)
    return int(m.group(1)) if m else None


def _parse_api_price(text: object) -> float | None:
    if text is None or pd.isna(text):
        return None
    value = str(text).translate(str.maketrans("０１２３４５６７８９，", "0123456789,"))
    m = _DIGIT_RE.search(value)
    if not m:
        return None
    return float(m.group(0).replace(",", ""))


def _nearest_prices(pts: gpd.GeoDataFrame, layer: gpd.GeoDataFrame,
                    price_col: str) -> pd.Series:
    joined = gpd.sjoin_nearest(
        pts,
        layer[[price_col, "geometry"]],
        how="left",
        max_distance=MAX_DIST_M,
        distance_col="_d",
    )
    return joined[~joined.index.duplicated(keep="first")][price_col]


def add_landprice(stations: pd.DataFrame, src_dir: Path | None = None) -> pd.DataFrame:
    """For each station: yearly official land price of the nearest 地価公示
    point within MAX_DIST_M, as {'years': [...], 'price': [...]} or None."""
    src_dir = Path(src_dir or config.RAW_DIR / "landprice")
    out = stations.copy()
    files = []
    if src_dir.exists():
        files.extend(sorted(src_dir.glob("L01-*.geojson")))
        files.extend(sorted(src_dir.glob("XPT002*.geojson")))
    if not files:
        out["landprice_series"] = None
        return out

    pts = gpd.GeoDataFrame(
        stations[[]].copy(),
        geometry=[Point(xy) for xy in zip(stations.lon, stations.lat)],
        crs=4326,
    ).to_crs(config.METRIC_CRS).reset_index(drop=True)

    _PRICE_MIN = 10_000      # ¥/m² — implausible floor
    _PRICE_MAX = 100_000_000  # ¥/m² — implausible ceiling

    per_station: list[dict] = [dict() for _ in range(len(stations))]
    for f in files:
        m = _YEAR_RE.search(f.name)
        if m is None and not f.name.startswith("XPT002"):
            continue
        lp = gpd.read_file(f)
        if lp.empty:
            continue
        lp = lp.to_crs(config.METRIC_CRS)

        if f.name.startswith("XPT002"):
            required = {"target_year_name_ja", "u_current_years_price_ja"}
            missing = required - set(lp.columns)
            if missing:
                raise ValueError(f"{f.name}: missing XPT002 columns {sorted(missing)}")
            lp["_year"] = lp["target_year_name_ja"].map(_parse_api_year)
            lp["_price"] = lp["u_current_years_price_ja"].map(_parse_api_price)
            lp = lp.dropna(subset=["_year", "_price"])
            for year, group in lp.groupby("_year"):
                prices = _nearest_prices(pts, group, "_price")
                for i in range(len(stations)):
                    price = prices.iloc[i]
                    if pd.notna(price):
                        per_station[i][int(year)] = float(price)
            continue

        year = int(m.group(1))
        # Per-year attribute override (L01-2024 moved price col from L01_006 → L01_008)
        price_attr = config.LANDPRICE_PRICE_ATTR_BY_YEAR.get(year, config.LANDPRICE_PRICE_ATTR)
        if price_attr not in lp.columns:
            raise ValueError(
                f"{f.name}: expected price attribute '{price_attr}' not found "
                f"(available: {sorted(lp.columns.tolist())}). "
                f"Update LANDPRICE_PRICE_ATTR_BY_YEAR in config.py for year {year}."
            )
        prices = _nearest_prices(pts, lp, price_attr)
        for i in range(len(stations)):
            price = prices.iloc[i]
            if pd.notna(price):
                fval = float(price)
                if not (_PRICE_MIN <= fval <= _PRICE_MAX):
                    raise ValueError(
                        f"{f.name}: implausible land price {fval} ¥/m² from attribute "
                        f"'{price_attr}' (valid range {_PRICE_MIN}–{_PRICE_MAX}). "
                        f"Likely attribute name drift — check LANDPRICE_PRICE_ATTR_BY_YEAR "
                        f"in config.py for year {year}."
                    )
                per_station[i][year] = fval

    series = []
    for rec in per_station:
        if not rec:
            series.append(None)
        else:
            years = sorted(rec)
            series.append({"years": years, "price": [rec[y] for y in years]})
    out["landprice_series"] = series
    return out
