import pandas as pd

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
    mask = pd.Series(True, index=df.index)
    for station, group in df.groupby("station"):
        med = group.ppsm.median()
        mad = (group.ppsm - med).abs().median()
        if mad > 0:
            z = 0.6745 * (group.ppsm - med) / mad
            mask.loc[group.index] = z.abs() <= k
    return df[mask]


def build_clean_transactions(con):
    df = con.execute("select * from raw_transactions").df()
    report = {"rows_in": len(df)}

    df = df[df.property_type.isin(config.PROPERTY_TYPES)]
    df = df[df.municipality.isin(config.TOKYO_23_WARDS)]
    df["quarter"] = df.period_text.map(parse_quarter)
    df["built_year"] = df.built_text.map(to_year)
    report["built_year_unparsed"] = int(df.built_year.isna().sum())
    df["minutes"] = pd.to_numeric(df.station_minutes, errors="coerce")
    df["price"] = pd.to_numeric(df.price_total, errors="coerce")
    df["area"] = pd.to_numeric(df.area_sqm, errors="coerce")
    df = df.dropna(subset=["quarter", "minutes", "price", "area"])
    df = df[(df.minutes <= config.MAX_STATION_MINUTES) & (df.area > 0)]
    df["ppsm"] = df.price / df.area
    df["qidx"] = df.quarter.map(qindex)
    df["station"] = df.station_name.map(norm_name)

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

    out = df[["station", "municipality", "qidx", "quarter", "ppsm", "price",
              "area", "built_year", "minutes", "price_type"]]
    con.register("_clean", out)
    con.execute("create or replace table clean_transactions as select * from _clean")
    con.unregister("_clean")
    return report
