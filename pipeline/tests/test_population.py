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
