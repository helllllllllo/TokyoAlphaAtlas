from atlas import config

def test_ward_list_complete():
    assert len(config.TOKYO_23_WARDS) == 23
    assert "足立区" in config.TOKYO_23_WARDS

def test_paths_are_inside_repo():
    assert config.OUT_DIR.name == "data"
    assert config.OUT_DIR.parent.name == "public"
