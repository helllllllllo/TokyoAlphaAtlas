from atlas.station_names import normalize

def test_nfkc_fullwidth():
    assert normalize("ＡＢＣ") == "ABC"

def test_ke_unification():
    assert normalize("霞ケ関") == "霞ヶ関"

def test_paren_stripped():
    assert normalize("押上（スカイツリー前）") == "押上"
    assert normalize("押上(スカイツリー前)") == "押上"

def test_eki_suffix_stripped():
    assert normalize("中野駅") == "中野"

def test_whitespace_and_empty():
    assert normalize(" 中野 ") == "中野"
    assert normalize("") == ""
    assert normalize(None) == ""

def test_alias_table_applied():
    from atlas import station_names
    station_names.ALIASES["テスト旧名"] = "テスト新名"
    assert normalize("テスト旧名") == "テスト新名"
    del station_names.ALIASES["テスト旧名"]
