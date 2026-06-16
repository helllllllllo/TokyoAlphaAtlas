from pathlib import Path

import pandas as pd
import pytest

from atlas import hazard

FIX = Path(__file__).parent / "fixtures"

STATIONS = pd.DataFrame({
    "name_norm": ["中野", "高円寺", "新宿テスト"],
    "lon": [139.6657, 139.6503, 139.7008],
    "lat": [35.7056, 35.7052, 35.6900],
})

def test_flood_full_coverage_rank2():
    df = hazard.add_hazard(STATIONS, flood_path=FIX / "a31_flood.geojson",
                           landslide_path=FIX / "a33_landslide.geojson")
    h = df.set_index("name_norm")
    nakano = h.loc["中野", "hazard_detail"]
    # buffer fully inside rank-2 polygon → weighted flood fraction = 0.5
    assert nakano["flood"] == pytest.approx(0.5, abs=0.02)
    assert nakano["landslide"] is False
    # score = 100 * (0.6*0.5 + 0.25*0 + 0.15*liq) renormalized w/o liquefaction:
    # (0.6*0.5)/(0.6+0.25)*100
    assert h.loc["中野", "hazard_score"] == pytest.approx(100 * 0.3 / 0.85, abs=2.0)

def test_landslide_flag():
    df = hazard.add_hazard(STATIONS, flood_path=FIX / "a31_flood.geojson",
                           landslide_path=FIX / "a33_landslide.geojson")
    h = df.set_index("name_norm")
    assert h.loc["高円寺", "hazard_detail"]["landslide"] is True
    assert h.loc["新宿テスト", "hazard_score"] == pytest.approx(0.0, abs=0.5)

def test_missing_files_degrade_to_none(tmp_path):
    df = hazard.add_hazard(STATIONS, flood_path=tmp_path / "nope.geojson",
                           landslide_path=tmp_path / "nope2.geojson")
    assert df.hazard_score.isna().all()


def test_api_hazard_fields_include_liquefaction_embankment_and_danger_zone(tmp_path):
    def write_geojson(name, properties):
        geom = {
            "type": "Polygon",
            "coordinates": [[
                [139.660, 35.700], [139.672, 35.700], [139.672, 35.712],
                [139.660, 35.712], [139.660, 35.700],
            ]],
        }
        (tmp_path / name).write_text(
            '{"type":"FeatureCollection","features":[{"type":"Feature","properties":'
            + __import__("json").dumps(properties)
            + ',"geometry":'
            + __import__("json").dumps(geom)
            + '}]}',
            encoding="utf-8",
        )

    write_geojson("flood.geojson", {"A31a_205": 3})
    write_geojson("liquefaction.geojson", {"liquefaction_tendency_level": 4})
    write_geojson("embankment.geojson", {"MORIDO": 1})
    write_geojson("danger_zone.geojson", {"A40_003": "災害危険区域"})

    df = hazard.add_hazard(
        STATIONS,
        flood_path=tmp_path / "flood.geojson",
        landslide_path=tmp_path / "missing.geojson",
        liquefaction_path=tmp_path / "liquefaction.geojson",
        embankment_path=tmp_path / "embankment.geojson",
        danger_zone_path=tmp_path / "danger_zone.geojson",
    )
    detail = df.set_index("name_norm").loc["中野", "hazard_detail"]

    assert detail["flood"] == pytest.approx(0.8, abs=0.05)
    assert detail["liquefaction"] == pytest.approx(0.8, abs=0.05)
    assert detail["embankment"] == pytest.approx(1.0, abs=0.05)
    assert detail["danger_zone"] is True
