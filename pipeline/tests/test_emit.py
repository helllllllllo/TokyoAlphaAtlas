import json
from pathlib import Path

import duckdb
import pytest

from atlas import aggregate, emit, ingest, normalize

FIX = Path(__file__).parent / "fixtures"

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
    assert not out.exists() or not any(out.iterdir())
