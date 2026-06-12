import numpy as np
import pandas as pd

from atlas import config


def asof_qidx(con) -> int:
    qidx = con.execute("select max(qidx) from clean_transactions").fetchone()[0]
    if qidx is None:
        raise ValueError("clean_transactions is empty — run normalize stage first")
    return qidx


def window_stats(con, start_qidx, end_qidx) -> pd.DataFrame:
    return con.execute("""
        select station,
               count(*)::int as n,
               median(ppsm) as median_ppsm,
               quantile_cont(ppsm, 0.25) as p25,
               quantile_cont(ppsm, 0.75) as p75
        from clean_transactions
        where qidx between ? and ?
        group by 1
    """, [start_qidx, end_qidx]).df()


def quarterly_medians(con) -> pd.DataFrame:
    return con.execute("""
        select station, qidx, median(ppsm) as med, count(*)::int as n
        from clean_transactions
        group by 1, 2
        order by 1, 2
    """).df()


def volatility(qmed: pd.DataFrame, asof: int, lookback=12) -> dict:
    """Stddev of QoQ log-changes of quarterly medians over the trailing window.
    Quarters with n < MIN_QUARTER_TX are excluded; only consecutive-quarter
    diffs count; None when fewer than MIN_VOL_OBS diffs."""
    recent = qmed[(qmed.qidx > asof - lookback) & (qmed.qidx <= asof)
                  & (qmed.n >= config.MIN_QUARTER_TX)]
    out = {}
    for st, g in recent.groupby("station"):
        g = g.sort_values("qidx")
        if (g.med.values <= 0).any():  # log undefined — keep the None contract
            out[st] = None
            continue
        consec = np.diff(g.qidx.values) == 1
        diffs = np.diff(np.log(g.med.values))[consec]
        out[st] = float(np.std(diffs, ddof=1)) if len(diffs) >= config.MIN_VOL_OBS else None
    return out


def build_price_snapshot(con, asof: int) -> pd.DataFrame:
    """Per-station price metrics as of `asof` (trailing 4Q windows)."""
    now = window_stats(con, asof - 3, asof)
    now = now.rename(columns={"n": "tx_count"})
    now["dispersion"] = (now.p75 - now.p25) / now.median_ppsm
    now["valid"] = now.tx_count >= config.MIN_WINDOW_TX

    for label, lag in (("growth_1y", 4), ("growth_3y", 12), ("growth_5y", 20)):
        then = window_stats(con, asof - 3 - lag, asof - lag)
        then = then[then.n >= config.MIN_WINDOW_TX][["station", "median_ppsm"]]
        then = then.rename(columns={"median_ppsm": "_then"})
        now = now.merge(then, on="station", how="left")
        now[label] = now.median_ppsm / now._then - 1
        now = now.drop(columns=["_then"])

    vol = volatility(quarterly_medians(con), asof)
    now["volatility"] = now.station.map(vol)
    now["dispersion"] = now.dispersion.replace([np.inf, -np.inf], np.nan)
    return now
