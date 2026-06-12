import json
import shutil
from pathlib import Path

import duckdb
import geopandas as gpd
import pytest

from atlas import aggregate, emit, ingest, normalize

FIX = Path(__file__).parent / "fixtures"

RAIL_OK = {"type": "FeatureCollection", "features": [
    {"type": "Feature",
     "properties": {"N02_003": "中央線", "N02_004": "東日本旅客鉄道"},
     "geometry": {"type": "LineString",
                  "coordinates": [[139.6650, 35.7056], [139.6660, 35.7056]]}}
]}

RAIL_BAD_COLS = {"type": "FeatureCollection", "features": [
    {"type": "Feature",
     "properties": {"foo": "bar"},
     "geometry": {"type": "LineString",
                  "coordinates": [[139.6650, 35.7056], [139.6660, 35.7056]]}}
]}

@pytest.fixture
def prepared(tmp_path):
    con = duckdb.connect()
    ingest.ingest_transactions(con, src_dir=FIX / "transactions")
    ingest.ingest_stations(con, n02_path=FIX / "n02_stations.geojson",
                           s12_path=FIX / "s12_ridership.geojson")
    report = normalize.build_clean_transactions(con)
    return con, report, tmp_path / "out"


def _hermetic_emit(con, report, out, tmp_path=None):
    """Call emit_all with empty/tmp paths so tests never read data/raw."""
    import tempfile
    td = tmp_path or Path(tempfile.mkdtemp())
    hz_empty = td / "_hz_empty"
    hz_empty.mkdir(exist_ok=True)
    emit.emit_all(con, report, out_dir=out,
                  rail_src=td / "_no_rail.geojson",
                  hazard_dir=hz_empty)

def test_emit_writes_valid_artifacts(prepared, tmp_path):
    con, report, out = prepared
    _hermetic_emit(con, report, out, tmp_path)
    stations = json.loads((out / "stations.json").read_text())
    assert stations["asof"] == "2023Q4"
    by_id = {s["id"]: s for s in stations["stations"]}
    assert by_id["中野"]["metrics"]["growth_1y"] == pytest.approx(0.10, abs=1e-6)
    assert by_id["中野"]["ward"] == "中野区"
    assert by_id["中野"]["metrics"]["hazard_score"] is None  # no hazard data loaded

    quarters = json.loads((out / "quarters.json").read_text())
    assert len(quarters["quarters"]) == 8
    assert quarters["stations"]["高円寺"]["m"][0] == pytest.approx(500000)

    detail = json.loads((out / "station" / "中野.json").read_text())
    assert detail["series"]["median_ppsm"][-1] == pytest.approx(660000)
    assert len(detail["similar"]) == 2  # only 2 other stations exist

    meta = json.loads((out / "meta.json").read_text())
    assert meta["asof"] == "2023Q4"
    # meta sources must now be structured objects (item 6)
    assert isinstance(meta["sources"]["transactions"], dict)
    assert "label" in meta["sources"]["transactions"]
    assert "rows_clean" in meta["sources"]["transactions"]
    assert isinstance(meta["sources"]["stations"], dict)
    assert "count" in meta["sources"]["stations"]
    assert isinstance(meta["sources"]["hazard"], bool)
    assert isinstance(meta["sources"]["population"], bool)
    assert isinstance(meta["sources"]["landprice"], bool)

def test_emit_validates_before_writing(prepared, monkeypatch, tmp_path):
    con, report, out = prepared
    # Sabotage the stations doc builder → validation must fail, nothing written
    monkeypatch.setattr(emit, "SCHEMA_VERSION", None)
    with pytest.raises(Exception):
        _hermetic_emit(con, report, out, tmp_path)
    assert not out.exists(), \
        f"emit wrote output despite validation failure: {sorted(out.iterdir())}"

def test_emit_rail_overlay_written(prepared, tmp_path):
    con, report, out = prepared
    rail_src = tmp_path / "rail_sections.geojson"
    rail_src.write_text(json.dumps(RAIL_OK))
    hz_empty = tmp_path / "hz_empty"
    hz_empty.mkdir()
    emit.emit_all(con, report, out_dir=out, rail_src=rail_src, hazard_dir=hz_empty)
    rail_out = out / "rail.geojson"
    assert rail_out.exists()
    rail = gpd.read_file(rail_out)
    assert set(rail.columns) >= {"line", "operator", "geometry"}
    assert rail.line.iloc[0] == "中央線"
    assert rail.operator.iloc[0] == "東日本旅客鉄道"

def test_emit_rail_overlay_missing_columns_skipped(prepared, tmp_path, capsys):
    con, report, out = prepared
    rail_src = tmp_path / "rail_sections.geojson"
    rail_src.write_text(json.dumps(RAIL_BAD_COLS))
    hz_empty = tmp_path / "hz_empty"
    hz_empty.mkdir()
    emit.emit_all(con, report, out_dir=out, rail_src=rail_src, hazard_dir=hz_empty)
    assert not (out / "rail.geojson").exists()
    # JSON artifacts still emitted
    assert (out / "stations.json").exists()
    assert "skipping overlay" in capsys.readouterr().out

def test_emit_hazard_overlay_written(prepared, tmp_path):
    con, report, out = prepared
    hz_dir = tmp_path / "hazard"
    hz_dir.mkdir()
    shutil.copy(FIX / "a31_flood.geojson", hz_dir / "flood.geojson")
    emit.emit_all(con, report, out_dir=out,
                  rail_src=tmp_path / "no_rail.geojson",
                  hazard_dir=hz_dir)
    flood_out = out / "hazard" / "flood.geojson"
    assert flood_out.exists()
    g = gpd.read_file(flood_out)
    assert len(g) == 1
    assert g.geometry.iloc[0].is_valid

def test_safe_id():
    assert emit._safe_id("A/B") == "A_B"
    assert emit._safe_id('a\\b:c*d?e"f<g>h|i#j%k') == "a_b_c_d_e_f_g_h_i_j_k"
    assert emit._safe_id("中野") == "中野"

def test_emit_unsafe_station_name_end_to_end(prepared, tmp_path):
    con, report, out = prepared
    # Rename a station to contain a path separator; ids must be sanitized
    # consistently across all artifacts while names keep the original string.
    con.execute("update clean_transactions set station = 'A/B' where station = '中野'")
    con.execute("update stations set name_norm = 'A/B' where name_norm = '中野'")
    _hermetic_emit(con, report, out, tmp_path)

    stations = json.loads((out / "stations.json").read_text())
    by_id = {s["id"]: s for s in stations["stations"]}
    assert "A_B" in by_id
    assert by_id["A_B"]["name"] == "A/B"

    quarters = json.loads((out / "quarters.json").read_text())
    assert "A_B" in quarters["stations"]
    assert "A/B" not in quarters["stations"]

    detail_path = out / "station" / "A_B.json"
    assert detail_path.exists()
    detail = json.loads(detail_path.read_text())
    assert detail["id"] == "A_B"
    assert detail["name"] == "A/B"

    # neighbors referencing the renamed station use the safe id + original name
    other = json.loads((out / "station" / "高円寺.json").read_text())
    sim_ids = {s["id"] for s in other["similar"]}
    sim_names = {s["name"] for s in other["similar"]}
    assert "A_B" in sim_ids
    assert "A/B" in sim_names
    for s in other["similar"]:
        if s["id"] == "A_B":
            assert s["median_ppsm"] == pytest.approx(660000)


def test_detail_includes_histogram(prepared, tmp_path):
    con, report, out = prepared
    _hermetic_emit(con, report, out, tmp_path)
    detail = json.loads((out / "station" / "中野.json").read_text())
    h = detail["hist"]
    assert h["window_quarters"] == 8
    assert len(h["bin_edges"]) == len(h["counts"]) + 1
    # 中野 trailing 8Q = 24 designed + 2 survivors = 26 rows after normalization
    assert sum(h["counts"]) == 26
    assert min(h["bin_edges"]) <= 540000 <= max(h["bin_edges"])


def test_detail_hist_null_when_thin(prepared, tmp_path):
    con, report, out = prepared
    # synthetic thin station: 5 rows only — below HIST_MIN_TX
    con.execute("""
        insert into clean_transactions
        select '薄い駅', municipality, qidx, quarter, ppsm, price, area, built_year, minutes, price_type
        from clean_transactions where station = '中野' limit 5
    """)
    con.execute("""
        insert into stations select '薄い駅', * exclude(name_norm) from stations where name_norm = '中野'
    """)
    _hermetic_emit(con, report, out, tmp_path)
    detail = json.loads((out / "station" / "薄い駅.json").read_text())
    assert detail["hist"] is None


def test_detail_hist_null_when_degenerate(prepared, tmp_path):
    con, report, out = prepared
    # synthetic station with >= HIST_MIN_TX rows but all-identical ppsm:
    # np.histogram on a zero-range sample yields meaningless bins → hist None
    con.execute("""
        insert into clean_transactions
        select '均一駅', municipality, qidx, quarter, 600000.0, price, area, built_year, minutes, price_type
        from clean_transactions where station = '中野'
    """)
    con.execute("""
        insert into stations select '均一駅', * exclude(name_norm) from stations where name_norm = '中野'
    """)
    _hermetic_emit(con, report, out, tmp_path)
    detail = json.loads((out / "station" / "均一駅.json").read_text())
    assert detail["hist"] is None


def test_zero_window_station_still_emitted(prepared, tmp_path):
    """Stations with only historical transactions (none in trailing 4Q) must
    still appear in stations.json with null median_ppsm, label データ薄,
    and a detail file with their full historical series."""
    con, report, out = prepared
    # Shift 高円寺 transactions to 2022 only — outside the trailing 4Q window
    # (asof = 2023Q4, window = 2023Q1–2023Q4)
    con.execute(
        "update clean_transactions set qidx = qidx - 8 where station = '高円寺'"
    )
    _hermetic_emit(con, report, out, tmp_path)

    stations = json.loads((out / "stations.json").read_text())
    by_id = {s["id"]: s for s in stations["stations"]}

    # 高円寺 must still be present
    assert "高円寺" in by_id, "zero-window station 高円寺 vanished from stations.json"
    entry = by_id["高円寺"]
    assert entry["metrics"]["median_ppsm"] is None
    assert entry["metrics"]["tx_count"] == 0
    assert entry["label"] == "データ薄"
    assert entry["metrics"]["confidence"] == 0
    assert entry["metrics"]["liquidity_score"] == 0.0

    # Detail file must exist
    detail_path = out / "station" / "高円寺.json"
    assert detail_path.exists(), "detail file for zero-window station missing"
    detail = json.loads(detail_path.read_text())
    # Historical series should have data (from the shifted 2022 rows)
    assert any(v is not None for v in detail["series"]["median_ppsm"])
    assert detail["similar"] == []
