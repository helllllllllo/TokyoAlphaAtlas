from pathlib import Path

import pandas as pd

from atlas import landprice

FIX = Path(__file__).parent / "fixtures"

STATIONS = pd.DataFrame({
    "name_norm": ["中野", "新宿テスト"],
    "lon": [139.6657, 139.7008],
    "lat": [35.7056, 35.6900],
})

def test_nearest_point_series():
    df = landprice.add_landprice(STATIONS, src_dir=FIX / "landprice")
    s = df.set_index("name_norm").loc["中野", "landprice_series"]
    assert s == {"years": [2023, 2024], "price": [800000.0, 850000.0]}

def test_too_far_gets_none():
    df = landprice.add_landprice(STATIONS, src_dir=FIX / "landprice")
    assert df.set_index("name_norm").loc["新宿テスト", "landprice_series"] is None

def test_missing_dir_degrades(tmp_path):
    df = landprice.add_landprice(STATIONS, src_dir=tmp_path)
    assert df.landprice_series.isna().all() or df.landprice_series.isnull().all()
