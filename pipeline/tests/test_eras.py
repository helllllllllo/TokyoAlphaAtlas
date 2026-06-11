from atlas.eras import to_year

def test_wareki():
    assert to_year("昭和60年") == 1985
    assert to_year("平成25年") == 2013
    assert to_year("令和元年") == 2019
    assert to_year("令和3年") == 2021

def test_seireki():
    assert to_year("2010年") == 2010

def test_unparseable_returns_none():
    assert to_year("") is None
    assert to_year(None) is None
    assert to_year("戦前") is None   # spec: never guess — count & exclude
    assert to_year("不明") is None
