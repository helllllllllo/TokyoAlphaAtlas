import gzip
import json

import geopandas as gpd

from atlas import api_geo


class FakeResponse:
    def __init__(self, body: bytes, headers: dict[str, str] | None = None):
        self.body = body
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


def test_fetch_mlit_tile_reads_existing_cache_without_network(tmp_path, monkeypatch):
    doc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"A33_001": 1}, "geometry": None}
    ]}
    cache_path = api_geo.tile_cache_path(tmp_path, "XKT029", 11, 1817, 806)
    cache_path.parent.mkdir(parents=True)
    cache_path.write_text(json.dumps(doc), encoding="utf-8")

    def fail_urlopen(*args, **kwargs):
        raise AssertionError("network should not be called for cached tiles")

    monkeypatch.setattr(api_geo.urllib.request, "urlopen", fail_urlopen)

    got = api_geo.fetch_mlit_tile(
        "XKT029", z=11, x=1817, y=806, cache_dir=tmp_path, api_key="unused"
    )

    assert got == doc


def test_fetch_mlit_tile_writes_gzip_response_to_cache(tmp_path, monkeypatch):
    doc = {"type": "FeatureCollection", "features": []}
    payload = gzip.compress(json.dumps(doc).encode("utf-8"))

    def fake_urlopen(req, timeout):
        assert req.headers["Ocp-apim-subscription-key"] == "secret"
        assert "XKT025" in req.full_url
        return FakeResponse(payload, {"Content-Encoding": "gzip"})

    monkeypatch.setattr(api_geo.urllib.request, "urlopen", fake_urlopen)

    got = api_geo.fetch_mlit_tile(
        "XKT025", z=11, x=1817, y=806, cache_dir=tmp_path, api_key="secret"
    )

    assert got == doc
    assert api_geo.tile_cache_path(tmp_path, "XKT025", 11, 1817, 806).exists()


def test_load_api_layer_merges_cached_tiles(tmp_path):
    feature = {
        "type": "Feature",
        "properties": {"plan_name": "駅前地区地区計画"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [139.66, 35.70], [139.67, 35.70], [139.67, 35.71],
                [139.66, 35.71], [139.66, 35.70],
            ]],
        },
    }
    cache_path = api_geo.tile_cache_path(tmp_path, "XKT023", 11, 1817, 806)
    cache_path.parent.mkdir(parents=True)
    cache_path.write_text(json.dumps({"type": "FeatureCollection", "features": [feature]}),
                          encoding="utf-8")

    gdf, count = api_geo.load_api_layer(
        "XKT023", cache_dir=tmp_path, tiles=[(11, 1817, 806)], api_key="unused"
    )

    assert count == 1
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert gdf.iloc[0]["plan_name"] == "駅前地区地区計画"
