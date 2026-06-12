import json
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
    # 81 rows = 72 designed (3 stations x 8 quarters x 3 tx) + 9 dirty
    assert n == 81
    cols = {r[0] for r in con.execute("describe raw_transactions").fetchall()}
    assert {"property_type", "municipality", "station_name", "station_minutes",
            "price_total", "area_sqm", "built_text", "period_text", "price_type"} <= cols
    # price_type defaulted when column absent in CSV — applies to all 81 rows
    assert con.execute(
        "select count(*) from raw_transactions where price_type = '取引価格情報'"
    ).fetchone()[0] == 81

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

def test_ingest_stations_without_s12(con, tmp_path):
    # S12 ridership file absent → stations table still written, ridership all null
    n = ingest.ingest_stations(con, n02_path=FIX / "n02_stations.geojson",
                               s12_path=tmp_path / "missing.geojson")
    assert n == 3
    rid = [r[0] for r in con.execute("select ridership from stations").fetchall()]
    assert len(rid) == 3
    assert all(r is None for r in rid)


def test_ingest_stations_bbox_clip(tmp_path):
    """Same-name stations inside and outside Tokyo bbox must not merge.
    The out-of-bbox entry (Kyushu coords) must be excluded entirely so the
    merged station has only-Tokyo coordinates and only in-bbox ridership."""
    # N02 fixture: 神田 appearing twice — once in Tokyo, once in Kyushu (fake)
    n02 = {
        "type": "FeatureCollection",
        "features": [
            # In-bbox: Tokyo 神田
            {"type": "Feature",
             "properties": {"N02_003": "中央線", "N02_004": "JR東日本", "N02_005": "神田"},
             "geometry": {"type": "LineString",
                          "coordinates": [[139.771, 35.692], [139.772, 35.692]]}},
            # Out-of-bbox: fake 神田 in Kyushu
            {"type": "Feature",
             "properties": {"N02_003": "鹿児島線", "N02_004": "JR九州", "N02_005": "神田"},
             "geometry": {"type": "LineString",
                          "coordinates": [[130.400, 33.600], [130.401, 33.600]]}},
        ],
    }
    # S12 fixture: ridership for 神田 — one in Tokyo (50000), one out-of-bbox (99999)
    s12 = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature",
             "properties": {"S12_001": "神田", "S12_033": 50000},
             "geometry": {"type": "Point", "coordinates": [139.771, 35.692]}},
            {"type": "Feature",
             "properties": {"S12_001": "神田", "S12_033": 99999},
             "geometry": {"type": "Point", "coordinates": [130.400, 33.600]}},
        ],
    }
    n02_path = tmp_path / "n02.geojson"
    s12_path = tmp_path / "s12.geojson"
    n02_path.write_text(json.dumps(n02))
    s12_path.write_text(json.dumps(s12))

    con = duckdb.connect()
    n = ingest.ingest_stations(con, n02_path=n02_path, s12_path=s12_path)
    assert n == 1  # only the Tokyo 神田 survives

    row = con.execute(
        "select lon, lat, ridership, lines from stations where name_norm = '神田'"
    ).fetchone()
    assert row is not None
    lon, lat, ridership, lines = row
    # Coords must be in Tokyo, not averaged with Kyushu
    assert 139.2 <= lon <= 140.2, f"lon {lon} outside Tokyo bbox"
    assert 35.3 <= lat <= 36.1, f"lat {lat} outside Tokyo bbox"
    # Ridership must only sum in-bbox entry (50000), not the Kyushu entry (99999)
    assert ridership == 50000, f"expected 50000, got {ridership}"
    # Lines must only include the Tokyo line
    assert "中央線" in lines
    assert "鹿児島線" not in lines


def test_ingest_stations_distant_homonyms_not_merged(tmp_path):
    """Same-name stations both inside the bbox but ~30km apart must not merge:
    only the member closest to Tokyo Station survives. A pair ~1km apart
    (legitimate multi-line station) still merges as before."""
    n02 = {
        "type": "FeatureCollection",
        "features": [
            # 霞ヶ関 in Chiyoda (close to Tokyo Station)
            {"type": "Feature",
             "properties": {"N02_003": "丸ノ内線", "N02_004": "東京地下鉄", "N02_005": "霞ヶ関"},
             "geometry": {"type": "LineString",
                          "coordinates": [[139.745, 35.674], [139.746, 35.674]]}},
            # 霞ヶ関 in Kawagoe — inside bbox but ~30km away
            {"type": "Feature",
             "properties": {"N02_003": "東武東上線", "N02_004": "東武鉄道", "N02_005": "霞ヶ関"},
             "geometry": {"type": "LineString",
                          "coordinates": [[139.448, 35.915], [139.449, 35.915]]}},
            # 中野 two line entries ~1km apart → must still merge
            {"type": "Feature",
             "properties": {"N02_003": "中央線", "N02_004": "東日本旅客鉄道", "N02_005": "中野"},
             "geometry": {"type": "LineString",
                          "coordinates": [[139.6657, 35.7056], [139.6667, 35.7056]]}},
            {"type": "Feature",
             "properties": {"N02_003": "東西線", "N02_004": "東京地下鉄", "N02_005": "中野"},
             "geometry": {"type": "LineString",
                          "coordinates": [[139.6740, 35.7100], [139.6750, 35.7100]]}},
        ],
    }
    s12 = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature",
             "properties": {"S12_001": "霞ヶ関", "S12_033": 80000},
             "geometry": {"type": "Point", "coordinates": [139.745, 35.674]}},
            # distant homonym's ridership must NOT be summed in
            {"type": "Feature",
             "properties": {"S12_001": "霞ヶ関", "S12_033": 7777},
             "geometry": {"type": "Point", "coordinates": [139.448, 35.915]}},
            {"type": "Feature",
             "properties": {"S12_001": "中野", "S12_033": 140000},
             "geometry": {"type": "Point", "coordinates": [139.6657, 35.7056]}},
        ],
    }
    n02_path = tmp_path / "n02.geojson"
    s12_path = tmp_path / "s12.geojson"
    n02_path.write_text(json.dumps(n02))
    s12_path.write_text(json.dumps(s12))

    con = duckdb.connect()
    n = ingest.ingest_stations(con, n02_path=n02_path, s12_path=s12_path)
    assert n == 2  # 霞ヶ関 (Chiyoda only) + 中野 (merged)

    lon, lat, ridership, lines = con.execute(
        "select lon, lat, ridership, lines from stations where name_norm = '霞ヶ関'"
    ).fetchone()
    # Chiyoda coords, not a Kawagoe-averaged midpoint
    assert abs(lon - 139.745) < 0.02 and abs(lat - 35.674) < 0.02
    assert ridership == 80000  # Kawagoe twin's 7777 not summed
    assert "丸ノ内線" in lines and "東武東上線" not in lines

    # legitimate close pair still merges with both lines
    lines_nakano, n_lines = con.execute(
        "select lines, n_lines from stations where name_norm = '中野'"
    ).fetchone()
    assert sorted(lines_nakano) == ["中央線", "東西線"]
    assert n_lines == 2
