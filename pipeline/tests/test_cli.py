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


def test_refresh_can_use_api_transaction_source(tmp_path, monkeypatch):
    calls = []

    def fake_api(con, **kwargs):
        calls.append(kwargs)
        from atlas import ingest
        return ingest.ingest_transactions(con, src_dir=FIX / "transactions")

    monkeypatch.setattr(cli.ingest, "ingest_transactions_api", fake_api)
    out = tmp_path / "data"
    empty_hz = tmp_path / "hazard"
    empty_hz.mkdir()

    cli.refresh(tx_source="api",
                api_from="2023Q1",
                api_to="2023Q4",
                n02_path=FIX / "n02_stations.geojson",
                s12_path=FIX / "s12_ridership.geojson",
                out_dir=out,
                db_path=tmp_path / "atlas.duckdb",
                hazard_dir=empty_hz,
                population_path=tmp_path / "missing_mesh.geojson",
                landprice_dir=tmp_path / "empty_landprice",
                rail_src=tmp_path / "missing_rail.geojson")

    assert calls == [{"from_period": "2023Q1", "to_period": "2023Q4"}]


def test_refresh_geo_source_api_prepares_api_layers(tmp_path, monkeypatch):
    calls = []
    out = tmp_path / "data"
    api_dir = tmp_path / "api_layers"
    hazard_dir = api_dir / "hazard"
    landprice_dir = api_dir / "landprice"
    redevelopment_dir = api_dir / "redevelopment"
    for p in (hazard_dir, landprice_dir, redevelopment_dir):
        p.mkdir(parents=True)
    population_path = api_dir / "population.geojson"
    population_path.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")

    def fake_prepare(**kwargs):
        calls.append(kwargs)
        return cli.api_geo.ApiGeoSources(
            hazard_dir=hazard_dir,
            population_path=population_path,
            landprice_dir=landprice_dir,
            redevelopment_dir=redevelopment_dir,
            overlay_hazard_dir=hazard_dir,
            overlay_redevelopment_dir=redevelopment_dir,
            tiles_fetched=7,
        )

    monkeypatch.setattr(cli.api_geo, "prepare_api_geo_sources", fake_prepare)

    cli.refresh(tx_dir=FIX / "transactions",
                n02_path=FIX / "n02_stations.geojson",
                s12_path=FIX / "s12_ridership.geojson",
                out_dir=out,
                db_path=tmp_path / "atlas.duckdb",
                rail_src=tmp_path / "missing_rail.geojson",
                geo_source="api",
                api_geo_force=True,
                api_geo_zoom=11)

    assert calls
    assert calls[0]["force"] is True
    assert calls[0]["default_zoom"] == 11
