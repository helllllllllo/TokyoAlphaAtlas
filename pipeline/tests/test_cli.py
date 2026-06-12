import json
from pathlib import Path

from atlas import cli

FIX = Path(__file__).parent / "fixtures"

def test_refresh_end_to_end(tmp_path, capsys):
    out = tmp_path / "data"
    # Pass empty/temp paths for hazard/population/landprice so the test
    # never reads from data/raw (hermetic: results must not depend on
    # production data being present).
    empty_hz = tmp_path / "hazard"
    empty_hz.mkdir()
    cli.refresh(tx_dir=FIX / "transactions",
                n02_path=FIX / "n02_stations.geojson",
                s12_path=FIX / "s12_ridership.geojson",
                out_dir=out,
                db_path=tmp_path / "atlas.duckdb",
                hazard_dir=empty_hz,
                population_path=tmp_path / "missing_mesh.geojson",
                landprice_dir=tmp_path / "empty_landprice",
                rail_src=tmp_path / "missing_rail.geojson")
    stations = json.loads((out / "stations.json").read_text())
    assert len(stations["stations"]) == 3
    printed = capsys.readouterr().out
    assert "match_rate" in printed
    assert "asof: 2023Q4" in printed
