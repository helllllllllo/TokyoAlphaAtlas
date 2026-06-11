import pandas as pd

VALUE_GAP = 0.10        # relative_value ≥ 10% cheaper than cohort
RESILIENCE_FLOOR = 30.0


def _num(x):
    return x is not None and not pd.isna(x)


def label_station(m: dict, ctx: dict) -> str:
    """Rule-based, priority-ordered. `ctx` holds cross-station percentile
    thresholds. The matched rule is transparent — shown on the station card."""
    if m["confidence"] == 0:
        return "データ薄"
    hazard = m["hazard_score"] if _num(m.get("hazard_score")) else 0.0
    resilience = m["pop_resilience"] if _num(m.get("pop_resilience")) else 50.0

    if _num(m.get("growth_1y")) and m["growth_1y"] >= ctx["growth_p75"] \
            and m["liquidity_score"] >= 50:
        return "モメンタム"
    if _num(m.get("relative_value")) and m["relative_value"] >= VALUE_GAP:
        risky = hazard > ctx["hazard_p50"] or resilience < RESILIENCE_FLOOR
        return "訳あり安値" if risky else "割安"
    if _num(m.get("volatility")) and m["volatility"] <= ctx["vol_p25"] \
            and m["liquidity_score"] >= 70 and m["gravity"] >= 70:
        return "安定コア"
    if m["median_ppsm"] >= ctx["price_p90"] and _num(m.get("growth_1y")) and m["growth_1y"] > 0:
        return "プレミアム"
    return "標準"


def label_all(df: pd.DataFrame) -> pd.DataFrame:
    ctx = {
        "growth_p75": df.growth_1y.dropna().quantile(0.75),
        "hazard_p50": df.hazard_score.dropna().quantile(0.5)
                      if "hazard_score" in df.columns and df.get("hazard_score") is not None
                         and df.hazard_score.notna().any() else 50.0,
        "vol_p25": df.volatility.dropna().quantile(0.25)
                   if df.volatility.notna().any() else 0.0,
        "price_p90": df.median_ppsm.quantile(0.9),
    }
    df = df.copy()
    df["label"] = [label_station(row, ctx) for row in df.to_dict("records")]
    return df
