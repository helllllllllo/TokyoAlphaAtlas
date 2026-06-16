from atlas import config

def test_ward_list_complete():
    assert len(config.TOKYO_23_WARDS) == 23
    assert "足立区" in config.TOKYO_23_WARDS

def test_region_scope_covers_saitama_and_kawasaki():
    assert config.REGION_LABEL == "Greater Tokyo"
    lon_min, lat_min, lon_max, lat_max = config.REGION_BBOX
    # Omiya / Saitama and Kawasaki should both be inside the default API scope.
    assert lon_min <= 139.6235 <= lon_max
    assert lat_min <= 35.9063 <= lat_max
    assert lon_min <= 139.6970 <= lon_max
    assert lat_min <= 35.5310 <= lat_max
    # Keep the legacy name as an alias for older pipeline call sites.
    assert config.TOKYO_BBOX == config.REGION_BBOX

def test_paths_are_inside_repo():
    assert config.OUT_DIR.name == "data"
    assert config.OUT_DIR.parent.name == "public"

def test_mlit_api_key_prefers_environment(monkeypatch):
    monkeypatch.setenv("MLIT_REAL_ESTATE_API_KEY", "from-env")
    assert config.get_mlit_api_key(dotenv_paths=[]) == "from-env"

def test_mlit_api_key_reads_dotenv_when_environment_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("MLIT_REAL_ESTATE_API_KEY", raising=False)
    monkeypatch.delenv("REAL_ESTATE_LIBRARY_API_KEY", raising=False)
    monkeypatch.delenv("MLIT_API_KEY", raising=False)
    dotenv = tmp_path / ".env"
    dotenv.write_text("# local secrets\nMLIT_REAL_ESTATE_API_KEY=from-dotenv\n", encoding="utf-8")
    assert config.get_mlit_api_key(dotenv_paths=[dotenv]) == "from-dotenv"
