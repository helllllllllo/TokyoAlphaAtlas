import json
from pathlib import Path

import pandas as pd
import pytest

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
    # 2024 fixture uses L01_008 (=850000); 2023 fixture uses L01_006 (=800000)
    assert s == {"years": [2023, 2024], "price": [800000.0, 850000.0]}

def test_too_far_gets_none():
    df = landprice.add_landprice(STATIONS, src_dir=FIX / "landprice")
    assert df.set_index("name_norm").loc["新宿テスト", "landprice_series"] is None

def test_missing_dir_degrades(tmp_path):
    df = landprice.add_landprice(STATIONS, src_dir=tmp_path)
    assert df.landprice_series.isna().all() or df.landprice_series.isnull().all()

def test_2024_uses_L01_008_attr(tmp_path):
    """L01-2024 file with L01_008 column → correct price read; L01_006=1 ignored."""
    lp_dir = tmp_path / "landprice"
    lp_dir.mkdir()
    feat = {"type": "FeatureCollection", "features": [
        {"type": "Feature",
         "properties": {"L01_006": 1, "L01_008": 920000},
         "geometry": {"type": "Point", "coordinates": [139.6660, 35.7050]}}
    ]}
    (lp_dir / "L01-2024.geojson").write_text(json.dumps(feat))
    st = pd.DataFrame({"name_norm": ["中野"], "lon": [139.6657], "lat": [35.7056]})
    df = landprice.add_landprice(st, src_dir=lp_dir)
    s = df.iloc[0]["landprice_series"]
    assert s == {"years": [2024], "price": [920000.0]}

def test_implausible_price_raises(tmp_path):
    """L01-2024 file where L01_008 contains an implausible value (e.g. 1) raises."""
    lp_dir = tmp_path / "landprice"
    lp_dir.mkdir()
    feat = {"type": "FeatureCollection", "features": [
        {"type": "Feature",
         "properties": {"L01_008": 1},
         "geometry": {"type": "Point", "coordinates": [139.6660, 35.7050]}}
    ]}
    (lp_dir / "L01-2024.geojson").write_text(json.dumps(feat))
    st = pd.DataFrame({"name_norm": ["中野"], "lon": [139.6657], "lat": [35.7056]})
    with pytest.raises(ValueError, match="implausible land price"):
        landprice.add_landprice(st, src_dir=lp_dir)

def test_missing_price_attr_raises(tmp_path):
    """File where the expected price attribute is absent raises with filename."""
    lp_dir = tmp_path / "landprice"
    lp_dir.mkdir()
    feat = {"type": "FeatureCollection", "features": [
        {"type": "Feature",
         "properties": {"L01_006": 800000},
         "geometry": {"type": "Point", "coordinates": [139.6660, 35.7050]}}
    ]}
    # Name it 2024 so the code expects L01_008
    (lp_dir / "L01-2024.geojson").write_text(json.dumps(feat))
    st = pd.DataFrame({"name_norm": ["中野"], "lon": [139.6657], "lat": [35.7056]})
    with pytest.raises(ValueError, match="L01-2024.geojson"):
        landprice.add_landprice(st, src_dir=lp_dir)


def test_xpt002_api_points_are_accepted(tmp_path):
    lp_dir = tmp_path / "landprice"
    lp_dir.mkdir()
    feat = {"type": "FeatureCollection", "features": [
        {"type": "Feature",
         "properties": {
             "target_year_name_ja": "令和6年1月1日",
             "u_current_years_price_ja": "920,000(円/㎡)",
         },
         "geometry": {"type": "Point", "coordinates": [139.6660, 35.7050]}},
        {"type": "Feature",
         "properties": {
             "target_year_name_ja": "令和5年1月1日",
             "u_current_years_price_ja": "870,000(円/㎡)",
         },
         "geometry": {"type": "Point", "coordinates": [139.6662, 35.7051]}},
    ]}
    (lp_dir / "XPT002.geojson").write_text(json.dumps(feat), encoding="utf-8")
    st = pd.DataFrame({"name_norm": ["中野"], "lon": [139.6657], "lat": [35.7056]})

    df = landprice.add_landprice(st, src_dir=lp_dir)

    assert df.iloc[0]["landprice_series"] == {
        "years": [2023, 2024],
        "price": [870000.0, 920000.0],
    }
