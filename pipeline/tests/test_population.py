from pathlib import Path

import pandas as pd
import pytest

from atlas import population

FIX = Path(__file__).parent / "fixtures"

STATIONS = pd.DataFrame({
    "name_norm": ["中野", "高円寺", "新宿テスト"],
    "lon": [139.6657, 139.6503, 139.7008],
    "lat": [35.7056, 35.7052, 35.6900],
})

def test_pop_change_weighted_by_intersection():
    df = population.add_population(STATIONS, mesh_path=FIX / "pop_mesh.geojson")
    p = df.set_index("name_norm")
    # 中野's 1km buffer lies mostly in the +10% cell
    assert p.loc["中野", "pop_change"] == pytest.approx(0.10, abs=0.05)
    # 高円寺 straddles both cells → between -20% and +10%, negative-leaning
    assert -0.20 <= p.loc["高円寺", "pop_change"] <= 0.10
    assert p.loc["中野", "pop_density"] > 0

def test_station_outside_mesh_gets_nan():
    df = population.add_population(STATIONS, mesh_path=FIX / "pop_mesh.geojson")
    assert pd.isna(df.set_index("name_norm").loc["新宿テスト", "pop_change"])

def test_missing_mesh_degrades(tmp_path):
    df = population.add_population(STATIONS, mesh_path=tmp_path / "nope.geojson")
    assert df.pop_change.isna().all()


def test_api_population_columns_are_auto_detected(tmp_path):
    mesh = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"PTN_2020": 100, "PTN_2050": 130},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [139.655, 35.695], [139.675, 35.695],
                    [139.675, 35.715], [139.655, 35.715],
                    [139.655, 35.695],
                ]],
            },
        }],
    }
    path = tmp_path / "mesh.geojson"
    path.write_text(__import__("json").dumps(mesh), encoding="utf-8")

    df = population.add_population(STATIONS, mesh_path=path)
    p = df.set_index("name_norm")

    assert p.loc["中野", "pop_change"] == pytest.approx(0.30, abs=0.05)
    assert p.loc["中野", "pop_density"] > 0
