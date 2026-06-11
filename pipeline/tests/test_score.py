import numpy as np
import pandas as pd
import pytest

from atlas import score

def test_haversine_tokyo_to_nakano():
    km = score.haversine_km(139.7671, 35.6812, 139.6657, 35.7056)
    assert km == pytest.approx(9.5, abs=0.5)

def test_pct_rank():
    s = pd.Series([10, 20, 30, 40])
    r = score.pct_rank(s)
    assert r.iloc[0] == 0.0
    assert r.iloc[-1] == 100.0

def test_confidence_tiers():
    assert score.confidence(35) == 2
    assert score.confidence(15) == 1
    assert score.confidence(5) == 0

def test_knn_similar_and_relative_value():
    df = pd.DataFrame({
        "station": list("ABCDE"),
        "median_ppsm": [500_000, 520_000, 510_000, 900_000, 905_000],
        "gravity": [50.0, 52.0, 48.0, 95.0, 94.0],
        "dist_tokyo_km": [10.0, 10.5, 9.8, 2.0, 2.1],
        "pop_density": [8000.0, 8100.0, 7900.0, 15000.0, 15100.0],
        "n_lines": [2, 2, 2, 6, 6],
    })
    out = score.add_similarity(df, k=2)
    sim_a = out.set_index("station").loc["A", "similar"]
    assert set(sim_a) == {"B", "C"}          # A's neighbors are the cheap suburbs, not the hubs
    rv_a = out.set_index("station").loc["A", "relative_value"]
    # cohort median of B,C = 515000 → (515000-500000)/515000
    assert rv_a == pytest.approx((515_000 - 500_000) / 515_000, rel=1e-6)

def test_knn_handles_missing_pop_density():
    df = pd.DataFrame({
        "station": list("ABC"),
        "median_ppsm": [1.0, 2.0, 3.0],
        "gravity": [1.0, 2.0, 3.0],
        "dist_tokyo_km": [1.0, 2.0, 3.0],
        "pop_density": [np.nan, np.nan, np.nan],
        "n_lines": [1, 2, 3],
    })
    out = score.add_similarity(df, k=1)
    assert out.similar.map(len).eq(1).all()
