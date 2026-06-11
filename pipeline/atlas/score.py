import numpy as np
import pandas as pd

from atlas import config

KNN_FEATURES = ["gravity", "dist_tokyo_km", "pop_density", "n_lines"]


def haversine_km(lon1, lat1, lon2, lat2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = p2 - p1
    dl = np.radians(lon2) - np.radians(lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def pct_rank(s: pd.Series) -> pd.Series:
    """0–100 percentile rank (min=0, max=100)."""
    if len(s) == 1:
        return pd.Series([50.0], index=s.index)
    return 100 * s.rank(method="average").sub(1) / (len(s) - 1)


def confidence(tx_count) -> int:
    if tx_count >= 30:
        return 2
    if tx_count >= config.MIN_WINDOW_TX:
        return 1
    return 0


def add_gravity(df: pd.DataFrame) -> pd.DataFrame:
    """gravity = mean of percentile(log ridership) and percentile(line count)."""
    rid = pd.to_numeric(df["ridership"], errors="coerce")
    rid_pct = pct_rank(np.log1p(rid.fillna(rid.median() if rid.notna().any() else 0)))
    line_pct = pct_rank(df["n_lines"].astype(float))
    df = df.copy()
    df["gravity"] = (rid_pct + line_pct) / 2
    return df


def add_similarity(df: pd.DataFrame, k: int = config.KNN_K) -> pd.DataFrame:
    """k-NN on z-scored non-price features → `similar` (list of station ids)
    and `relative_value` = (cohort_median − own) / cohort_median."""
    df = df.reset_index(drop=True).copy()
    X = df[KNN_FEATURES].astype(float).copy()
    for c in KNN_FEATURES:
        col = X[c]
        col = col.fillna(col.median()) if col.notna().any() else col.fillna(0.0)
        std = col.std(ddof=0)
        X[c] = (col - col.mean()) / std if std > 0 else 0.0
    M = X.values
    D = ((M[:, None, :] - M[None, :, :]) ** 2).sum(axis=-1)
    np.fill_diagonal(D, np.inf)
    k = min(k, len(df) - 1)
    order = np.argsort(D, axis=1)[:, :k]

    similar, rel_value = [], []
    for i in range(len(df)):
        idx = order[i]
        similar.append(df.station.iloc[idx].tolist())
        cohort = df.median_ppsm.iloc[idx].median()
        own = df.median_ppsm.iloc[i]
        rel_value.append(float((cohort - own) / cohort) if cohort and not np.isnan(cohort) else None)
    df["similar"] = similar
    df["relative_value"] = rel_value
    return df


def build_scores(snapshot: pd.DataFrame, stations: pd.DataFrame) -> pd.DataFrame:
    """Join price snapshot to station attributes and compute all scores.
    `stations` columns: name_norm, lon, lat, lines, n_lines, n_operators, ridership
    (+ optional pop_density, pop_change, hazard_score, hazard_detail)."""
    df = snapshot.merge(stations.rename(columns={"name_norm": "station"}),
                        on="station", how="inner")
    df["liquidity_score"] = pct_rank(df.tx_count.astype(float))
    df["dist_tokyo_km"] = haversine_km(df.lon, df.lat, *config.TOKYO_STATION)
    df = add_gravity(df)
    if "pop_density" not in df.columns:
        df["pop_density"] = np.nan
    if "pop_change" in df.columns:
        df["pop_resilience"] = pct_rank(df.pop_change.astype(float).fillna(df.pop_change.median()))
    else:
        df["pop_resilience"] = None
    df = add_similarity(df)
    df["confidence"] = df.tx_count.map(confidence)
    return df
