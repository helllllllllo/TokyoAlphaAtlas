from pathlib import Path

import duckdb
import pytest

from atlas import ingest

FIX = Path(__file__).parent / "fixtures"

@pytest.fixture
def con():
    return duckdb.connect()

def test_ingest_transactions(con):
    n = ingest.ingest_transactions(con, src_dir=FIX / "transactions")
    assert n == 78
    cols = {r[0] for r in con.execute("describe raw_transactions").fetchall()}
    assert {"property_type", "municipality", "station_name", "station_minutes",
            "price_total", "area_sqm", "built_text", "period_text", "price_type"} <= cols
    # price_type defaulted when column absent in CSV
    assert con.execute(
        "select count(*) from raw_transactions where price_type = '取引価格情報'"
    ).fetchone()[0] == 78

def test_ingest_transactions_empty_dir_raises(con, tmp_path):
    with pytest.raises(FileNotFoundError):
        ingest.ingest_transactions(con, src_dir=tmp_path)

def test_ingest_stations_merges_lines(con):
    n = ingest.ingest_stations(con, n02_path=FIX / "n02_stations.geojson",
                               s12_path=FIX / "s12_ridership.geojson")
    assert n == 3  # 中野's two line entries merged into one logical station
    row = con.execute(
        "select lines, n_lines, ridership, lon from stations where name_norm = '中野'"
    ).fetchone()
    assert sorted(row[0]) == ["中央線", "東西線"]
    assert row[1] == 2
    assert row[2] == 140000
    assert 139.66 < row[3] < 139.67
