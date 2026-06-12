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

def test_emit_writes_valid_artifacts(prepared):
    con, report, out = prepared
    emit.emit_all(con, report, out_dir=out)
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

def test_emit_validates_before_writing(prepared, monkeypatch):
    con, report, out = prepared
    # Sabotage the stations doc builder → validation must fail, nothing written
    monkeypatch.setattr(emit, "SCHEMA_VERSION", None)
    with pytest.raises(Exception):
        emit.emit_all(con, report, out_dir=out)
    assert not out.exists(), \
        f"emit wrote output despite validation failure: {sorted(out.iterdir())}"

def test_emit_rail_overlay_written(prepared, tmp_path):
    con, report, out = prepared
    rail_src = tmp_path / "rail_sections.geojson"
    rail_src.write_text(json.dumps(RAIL_OK))
    emit.emit_all(con, report, out_dir=out, rail_src=rail_src)
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
    emit.emit_all(con, report, out_dir=out, rail_src=rail_src)
    assert not (out / "rail.geojson").exists()
    # JSON artifacts still emitted
    assert (out / "stations.json").exists()
    assert "skipping overlay" in capsys.readouterr().out

def test_emit_hazard_overlay_written(prepared, tmp_path):
    con, report, out = prepared
    hz_dir = tmp_path / "hazard"
    hz_dir.mkdir()
    shutil.copy(FIX / "a31_flood.geojson", hz_dir / "flood.geojson")
    emit.emit_all(con, report, out_dir=out, hazard_dir=hz_dir)
    flood_out = out / "hazard" / "flood.geojson"
    assert flood_out.exists()
    g = gpd.read_file(flood_out)
    assert len(g) == 1
    assert g.geometry.iloc[0].is_valid

def test_safe_id():
    assert emit._safe_id("A/B") == "A_B"
    assert emit._safe_id('a\\b:c*d?e"f<g>h|i#j%k') == "a_b_c_d_e_f_g_h_i_j_k"
    assert emit._safe_id("中野") == "中野"

def test_emit_unsafe_station_name_end_to_end(prepared):
    con, report, out = prepared
    # Rename a station to contain a path separator; ids must be sanitized
    # consistently across all artifacts while names keep the original string.
    con.execute("update clean_transactions set station = 'A/B' where station = '中野'")
    con.execute("update stations set name_norm = 'A/B' where name_norm = '中野'")
    emit.emit_all(con, report, out_dir=out)

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
