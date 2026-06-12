import json
from pathlib import Path

from atlas import cli

FIX = Path(__file__).parent / "fixtures"

def test_refresh_end_to_end(tmp_path, capsys):
    out = tmp_path / "data"
    cli.refresh(tx_dir=FIX / "transactions",
                n02_path=FIX / "n02_stations.geojson",
                s12_path=FIX / "s12_ridership.geojson",
                out_dir=out,
                db_path=tmp_path / "atlas.duckdb")
    stations = json.loads((out / "stations.json").read_text())
    assert len(stations["stations"]) == 3
    printed = capsys.readouterr().out
    assert "match_rate" in printed
    assert "asof: 2023Q4" in printed
