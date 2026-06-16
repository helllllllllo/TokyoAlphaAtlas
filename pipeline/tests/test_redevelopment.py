import json
from pathlib import Path

import pandas as pd

from atlas import redevelopment


FIX = Path(__file__).parent / "fixtures"

STATIONS = pd.DataFrame({
    "name_norm": ["中野", "新宿テスト"],
    "lon": [139.6657, 139.7008],
    "lat": [35.7056, 35.6900],
    "pop_change": [0.10, -0.05],
    "landprice_series": [
        {"years": [2023, 2024], "price": [800000.0, 920000.0]},
        None,
    ],
})


def write_geojson(path: Path, features: list[dict]):
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}),
                    encoding="utf-8")


def polygon_feature(properties: dict, lon=139.6657, lat=35.7056, delta=0.006):
    return {
        "type": "Feature",
        "properties": properties,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [lon - delta, lat - delta], [lon + delta, lat - delta],
                [lon + delta, lat + delta], [lon - delta, lat + delta],
                [lon - delta, lat - delta],
            ]],
        },
    }


def line_feature(properties: dict):
    return {
        "type": "Feature",
        "properties": properties,
        "geometry": {
            "type": "LineString",
            "coordinates": [[139.660, 35.705], [139.672, 35.706]],
        },
    }


def test_redevelopment_score_uses_planning_layers(tmp_path):
    write_geojson(tmp_path / "zoning.geojson", [
        polygon_feature({
            "use_area_ja": "商業地域",
            "u_floor_area_ratio_ja": "800%",
            "u_building_coverage_ratio_ja": "80%",
        })
    ])
    write_geojson(tmp_path / "district_plan.geojson", [
        polygon_feature({"plan_name": "中野駅前地区地区計画"})
    ])
    write_geojson(tmp_path / "high_utilization.geojson", [
        polygon_feature({"advanced_name": "中野駅前高度利用地区"})
    ])
    write_geojson(tmp_path / "city_roads.geojson", [
        line_feature({"planning_road_ja": "都市計画道路", "decision_date": "2024/01/01"})
    ])

    df = redevelopment.add_redevelopment(STATIONS, src_dir=tmp_path)
    row = df.set_index("name_norm").loc["中野"]

    assert row["redevelopment_score"] >= 70
    assert row["planning_intensity"] > 0
    assert row["redevelopment_detail"]["zoning"]["use_area"] == "商業地域"
    assert row["redevelopment_detail"]["district_plan"]["count"] == 1
    assert row["redevelopment_detail"]["high_utilization"]["count"] == 1
    assert row["redevelopment_detail"]["city_roads"]["count"] == 1


def test_redevelopment_missing_layers_degrades(tmp_path):
    df = redevelopment.add_redevelopment(STATIONS, src_dir=tmp_path)
    assert df.redevelopment_score.isna().all()
    assert df.redevelopment_detail.isna().all() or df.redevelopment_detail.isnull().all()
