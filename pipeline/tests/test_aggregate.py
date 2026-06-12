from pathlib import Path

import duckdb
import numpy as np
import pytest

from atlas import aggregate, ingest, normalize

FIX = Path(__file__).parent / "fixtures"

@pytest.fixture
def con():
    c = duckdb.connect()
    ingest.ingest_transactions(c, src_dir=FIX / "transactions")
    ingest.ingest_stations(c, n02_path=FIX / "n02_stations.geojson",
                           s12_path=FIX / "s12_ridership.geojson")
    normalize.build_clean_transactions(c)
    return c

def test_asof_quarter(con):
    assert aggregate.asof_qidx(con) == 2023 * 4 + 3  # 2023Q4

def test_window_stats(con):
    asof = aggregate.asof_qidx(con)
    w = aggregate.window_stats(con, asof - 3, asof).set_index("station")
    assert w.loc["中野", "median_ppsm"] == pytest.approx(660000)
    assert w.loc["中野", "n"] == 14  # 12 designed + 2 survivor rows (不明/blank 建築年, both pinned at median ppsm)
    assert w.loc["高円寺", "median_ppsm"] == pytest.approx(500000)

def test_growth_exact(con):
    asof = aggregate.asof_qidx(con)
    snap = aggregate.build_price_snapshot(con, asof).set_index("station")
    assert snap.loc["中野", "growth_1y"] == pytest.approx(0.10, abs=1e-6)
    assert snap.loc["高円寺", "growth_1y"] == pytest.approx(0.0, abs=1e-6)
    assert np.isnan(snap.loc["中野", "growth_3y"])  # fixture has only 2 years

def test_quarterly_series(con):
    qm = aggregate.quarterly_medians(con)
    nakano = qm[qm.station == "中野"].sort_values("qidx")
    assert len(nakano) == 8
    assert nakano.med.iloc[0] == pytest.approx(600000)
    assert nakano.med.iloc[-1] == pytest.approx(660000)

def test_volatility_unit():
    import pandas as pd
    rows = []
    med = 100000.0
    for i, sign in enumerate([1, -1, 1, -1, 1, -1, 1]):
        rows.append({"station": "X", "qidx": 8000 + i, "med": med, "n": 5})
        med *= np.exp(sign * 0.1)
    qm = pd.DataFrame(rows)
    vol = aggregate.volatility(qm, asof=8006)
    assert vol["X"] == pytest.approx(np.std([0.1, -0.1, 0.1, -0.1, 0.1, -0.1], ddof=1), rel=1e-3)

def test_volatility_zero_median_returns_none():
    import pandas as pd
    rows = [{"station": "X", "qidx": 8000 + i, "med": m, "n": 5}
            for i, m in enumerate([100000.0, 0.0, 100000.0, 110000.0,
                                   105000.0, 102000.0, 108000.0])]
    qm = pd.DataFrame(rows)
    vol = aggregate.volatility(qm, asof=8006)
    assert vol["X"] is None

def test_asof_empty_table_raises():
    import duckdb
    c = duckdb.connect()
    c.execute("create table clean_transactions (qidx int)")
    with pytest.raises(ValueError, match="clean_transactions is empty"):
        aggregate.asof_qidx(c)
