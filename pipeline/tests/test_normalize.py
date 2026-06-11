from pathlib import Path

import duckdb
import pytest

from atlas import ingest, normalize

FIX = Path(__file__).parent / "fixtures"

@pytest.fixture
def con():
    c = duckdb.connect()
    ingest.ingest_transactions(c, src_dir=FIX / "transactions")
    ingest.ingest_stations(c, n02_path=FIX / "n02_stations.geojson",
                           s12_path=FIX / "s12_ridership.geojson")
    return c

def test_clean_filters_and_ppsm(con):
    report = normalize.build_clean_transactions(con)
    df = con.execute("select * from clean_transactions").df()
    # 72 designed rows + 1 unparseable-built-year row survive;
    # dropped: wrong type, non-23区, bad distance, MAD outlier, unknown station
    assert len(df) == 73
    assert set(df.station) == {"中野", "高円寺", "新宿テスト"}
    assert df[(df.station == "中野") & (df.qidx == 2023 * 4 + 3)].ppsm.median() == pytest.approx(630000)
    assert report["rows_in"] == 78
    assert report["match_rate"] > 0.97
    assert report["built_year_unparsed"] == 1

def test_mad_outlier_removed(con):
    normalize.build_clean_transactions(con)
    mx = con.execute("select max(ppsm) from clean_transactions").fetchone()[0]
    assert mx < 2_000_000  # the 19.8M ppsm plant is gone

def test_match_gate_raises():
    c = duckdb.connect()
    ingest.ingest_transactions(c, src_dir=FIX / "transactions")
    # station table missing 高円寺 → match rate falls below 0.97
    c.execute("""create or replace table stations as
                 select '中野' as name_norm, 139.66 lon, 35.70 lat,
                        ['中央線'] lines, 1 n_lines, 1 n_operators, 140000 ridership""")
    with pytest.raises(normalize.MatchRateError) as ei:
        normalize.build_clean_transactions(c)
    assert "高円寺" in str(ei.value)
