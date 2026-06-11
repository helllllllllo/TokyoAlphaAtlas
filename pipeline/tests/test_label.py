import pandas as pd
import pytest

from atlas.label import label_station, label_all

CTX = {"growth_p75": 0.06, "hazard_p50": 40.0, "vol_p25": 0.02, "price_p90": 1_200_000}

def base(**over):
    m = {"confidence": 2, "growth_1y": 0.03, "liquidity_score": 60.0,
         "relative_value": 0.0, "hazard_score": 30.0, "pop_resilience": 50.0,
         "volatility": 0.05, "gravity": 60.0, "median_ppsm": 800_000}
    m.update(over)
    return m

def test_thin_data_first():
    assert label_station(base(confidence=0, growth_1y=0.5), CTX) == "データ薄"

def test_momentum():
    assert label_station(base(growth_1y=0.09), CTX) == "モメンタム"

def test_value():
    assert label_station(base(relative_value=0.15, hazard_score=20.0), CTX) == "割安"

def test_risky_cheap():
    assert label_station(base(relative_value=0.15, hazard_score=70.0), CTX) == "訳あり安値"
    assert label_station(base(relative_value=0.15, hazard_score=20.0, pop_resilience=10.0), CTX) == "訳あり安値"

def test_stable_core():
    assert label_station(base(volatility=0.01, liquidity_score=80.0, gravity=85.0), CTX) == "安定コア"

def test_premium():
    assert label_station(base(median_ppsm=1_500_000, growth_1y=0.02), CTX) == "プレミアム"

def test_default():
    assert label_station(base(), CTX) == "標準"

def test_none_metrics_fall_through():
    assert label_station(base(growth_1y=None, volatility=None, relative_value=None), CTX) == "標準"

def test_label_all_builds_context():
    df = pd.DataFrame([base(growth_1y=g, median_ppsm=p)
                       for g, p in [(0.01, 500_000), (0.02, 600_000), (0.03, 700_000),
                                    (0.20, 800_000), (0.04, 900_000)]])
    out = label_all(df)
    assert "label" in out.columns and len(out) == 5
