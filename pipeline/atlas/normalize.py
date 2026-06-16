import pandas as pd
import numpy as np

from atlas import config
from atlas.eras import to_year
from atlas.quarters import parse_quarter, qindex
from atlas.station_names import normalize as norm_name


class MatchRateError(RuntimeError):
    def __init__(self, rate, unmatched_counts):
        self.rate = rate
        self.unmatched = unmatched_counts
        lines = "\n".join(f"  {name}: {n}" for name, n in unmatched_counts.items())
        super().__init__(
            f"station match rate {rate:.4f} < gate {config.MATCH_RATE_GATE}.\n"
            f"Top unmatched names (extend atlas/station_names.py ALIASES):\n{lines}"
        )


def mad_trim(df, k=config.MAD_K):
    g = df.groupby("station")["ppsm"]
    med = g.transform("median")
    mad = (df["ppsm"] - med).abs().groupby(df["station"]).transform("median")
    has_spread = mad > 0
    # MAD==0: zero spread → keep all; extreme outliers in zero-spread stations
    # pass through (accepted: rare, and trailing-window medians absorb them)
    z = pd.Series(0.0, index=df.index)
    z[has_spread] = 0.6745 * (df.loc[has_spread, "ppsm"] - med[has_spread]) / mad[has_spread]
    return df[z.abs() <= k]


def _nearest_station_names(con, lon: pd.Series, lat: pd.Series) -> pd.Series:
    stations = con.execute("select name_norm, lon, lat from stations").df()
    if stations.empty:
        return pd.Series("", index=lon.index)
    st_lon = stations.lon.astype(float).to_numpy()
    st_lat = stations.lat.astype(float).to_numpy()
    st_names = stations.name_norm.to_numpy()
    cache: dict[tuple[float, float], str] = {}
    out = []
    for idx in lon.index:
        key = (round(float(lon.loc[idx]), 7), round(float(lat.loc[idx]), 7))
        if key not in cache:
            lon0 = np.radians(key[0])
            lat0 = np.radians(key[1])
            lon1 = np.radians(st_lon)
            lat1 = np.radians(st_lat)
            dlon = lon1 - lon0
            dlat = lat1 - lat0
            a = np.sin(dlat / 2) ** 2 + np.cos(lat0) * np.cos(lat1) * np.sin(dlon / 2) ** 2
            dist = 2 * np.arcsin(np.sqrt(a))
            cache[key] = str(st_names[int(np.argmin(dist))])
        out.append(cache[key])
    return pd.Series(out, index=lon.index)


def _point_in_region(lon: pd.Series, lat: pd.Series) -> pd.Series:
    lon_min, lat_min, lon_max, lat_max = config.REGION_BBOX
    return lon.between(lon_min, lon_max) & lat.between(lat_min, lat_max)


def _station_text_lookup(con) -> dict[str, str]:
    if "stations" not in {r[0] for r in con.execute("show tables").fetchall()}:
        return {}
    cols = set(con.execute("describe stations").df()["column_name"])
    if "base_name_norm" in cols:
        stations = con.execute(
            "select name_norm, base_name_norm, lon, lat from stations"
        ).df()
    else:
        stations = con.execute(
            "select name_norm, name_norm as base_name_norm, lon, lat from stations"
        ).df()

    known = set(stations.name_norm)
    lookup = {name: name for name in known}
    lon0, lat0 = config.TOKYO_STATION
    for base, group in stations.groupby("base_name_norm"):
        if base in known:
            continue
        if len(group) == 1:
            lookup[base] = str(group.name_norm.iloc[0])
            continue
        lon = group.lon.astype(float).to_numpy()
        lat = group.lat.astype(float).to_numpy()
        lon0r = np.radians(lon0)
        lat0r = np.radians(lat0)
        lon1 = np.radians(lon)
        lat1 = np.radians(lat)
        dlon = lon1 - lon0r
        dlat = lat1 - lat0r
        a = np.sin(dlat / 2) ** 2 + np.cos(lat0r) * np.cos(lat1) * np.sin(dlon / 2) ** 2
        lookup[base] = str(group.name_norm.iloc[int(np.argmin(2 * np.arcsin(np.sqrt(a))))])
    return lookup


def build_clean_transactions(con):
    df = con.execute("select * from raw_transactions").df()
    report = {"rows_in": len(df)}
    for col in ("station_lon", "station_lat"):
        if col not in df.columns:
            df[col] = None

    df = df[df.property_type.isin(config.PROPERTY_TYPES)]
    df["quarter"] = df.period_text.map(parse_quarter)
    df["built_year"] = df.built_text.map(to_year)
    report["built_year_unparsed"] = int(df.built_year.isna().sum())
    df["minutes"] = pd.to_numeric(df.station_minutes, errors="coerce")
    df["price"] = pd.to_numeric(df.price_total, errors="coerce")
    df["area"] = pd.to_numeric(df.area_sqm, errors="coerce")
    df["station_lon_num"] = pd.to_numeric(df.station_lon, errors="coerce")
    df["station_lat_num"] = pd.to_numeric(df.station_lat, errors="coerce")
    has_point = df.station_lon_num.notna() & df.station_lat_num.notna()
    in_region = has_point & _point_in_region(df.station_lon_num, df.station_lat_num)
    legacy_text_row = (~has_point) & df.municipality.isin(config.LEGACY_TEXT_MUNICIPALITIES)
    df = df[in_region | legacy_text_row]
    df = df.dropna(subset=["quarter", "price", "area"])
    has_usable_distance = df.minutes.notna() & (df.minutes <= config.MAX_STATION_MINUTES)
    has_point = df.station_lon_num.notna() & df.station_lat_num.notna()
    df = df[((has_usable_distance) | has_point) & (df.area > 0)]
    point_without_minutes = df.minutes.isna() & df.station_lon_num.notna() & df.station_lat_num.notna()
    df.loc[point_without_minutes, "minutes"] = 0.0
    df["ppsm"] = df.price / df.area
    df["qidx"] = df.quarter.map(qindex)
    df["station"] = df.station_name.map(norm_name)
    needs_point_station = (df.station == "") & df.station_lon_num.notna() & df.station_lat_num.notna()
    if needs_point_station.any():
        df.loc[needs_point_station, "station"] = _nearest_station_names(
            con,
            df.loc[needs_point_station, "station_lon_num"],
            df.loc[needs_point_station, "station_lat_num"],
        )
    lookup = _station_text_lookup(con)
    df["station"] = df.station.map(lambda s: lookup.get(s, s))

    # rows with no usable station name are unattributable — drop before the
    # match-rate computation so they don't poison the gate
    no_station = df.station == ""
    report["no_station"] = int(no_station.sum())
    df = df[~no_station]

    if df.empty:
        raise ValueError(
            "no rows survived filtering — check PROPERTY_TYPES/REGION_BBOX config"
        )

    known = set(con.execute("select name_norm from stations").df().name_norm)
    matched = df.station.isin(known)
    rate = float(matched.mean())
    report["match_rate"] = rate
    if rate < config.MATCH_RATE_GATE:
        top = df.loc[~matched, "station"].value_counts().head(50).to_dict()
        raise MatchRateError(rate, top)
    df = df[matched]

    before = len(df)
    df = mad_trim(df)
    report["mad_trimmed"] = before - len(df)
    report["rows_out"] = len(df)

    # district stays in raw_transactions only — not needed downstream yet
    out = df[["station", "municipality", "qidx", "quarter", "ppsm", "price",
              "area", "built_year", "minutes", "price_type"]]
    con.register("_clean", out)
    con.execute("create or replace table clean_transactions as select * from _clean")
    con.unregister("_clean")
    return report
