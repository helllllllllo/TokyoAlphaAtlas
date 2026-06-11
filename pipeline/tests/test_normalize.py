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
    # 74 rows = 72 designed + 不明-built-year row + blank-built-year row
    # (built_year=None is reported, not dropped); dropped: wrong type, non-23区,
    # bad distance, MAD outlier, unknown station, blank station, blank period
    assert len(df) == 74
    assert set(df.station) == {"中野", "高円寺", "新宿テスト"}
    # 中野 2023Q4 ppsm = [594000, 660000(不明), 660000(blank year), 660000, 726000]
    # — survivor rows are pinned AT the designed 2023 median (660000), so the
    # quarter median stays at the designed value
    assert df[(df.station == "中野") & (df.qidx == 2023 * 4 + 3)].ppsm.median() == pytest.approx(660000)
    assert report["rows_in"] == 81  # 72 designed + 9 dirty
    assert report["match_rate"] > 0.97
    # 不明 row + blank-建築年 row
    assert report["built_year_unparsed"] == 2
    # blank 最寄駅：名称 row — unattributable, dropped before the match-rate gate
    assert report["no_station"] == 1

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

def test_empty_after_filters_raises():
    c = duckdb.connect()
    # single row whose property type is filtered out → nothing survives
    c.execute("""create or replace table raw_transactions as
                 select '宅地(土地と建物)' as property_type, '中野区' as municipality,
                        'x' as district, '中野' as station_name, '5' as station_minutes,
                        '30000000' as price_total, '50' as area_sqm,
                        '平成2年' as built_text, '2023年第4四半期' as period_text,
                        '取引価格情報' as price_type""")
    with pytest.raises(ValueError, match="no rows survived filtering"):
        normalize.build_clean_transactions(c)

def test_mad_zero_spread_keeps_outlier():
    import pandas as pd
    # MAD==0 (zero spread) → keep all rows, even an extreme outlier; documented
    # behavior: trailing-window medians absorb such rare pass-throughs
    df = pd.DataFrame({"station": ["X"] * 5,
                       "ppsm": [100_000.0] * 4 + [99_000_000.0]})
    out = normalize.mad_trim(df)
    assert len(out) == 5
