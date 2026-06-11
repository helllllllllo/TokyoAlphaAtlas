import pytest

from atlas.quarters import parse_quarter, qindex, qlabel

def test_parse_seireki_fullwidth():
    assert parse_quarter("2023年第３四半期") == "2023Q3"

def test_parse_seireki_halfwidth():
    assert parse_quarter("2008年第2四半期") == "2008Q2"

def test_parse_wareki():
    assert parse_quarter("平成25年第１四半期") == "2013Q1"

def test_parse_garbage():
    assert parse_quarter("") is None
    assert parse_quarter(None) is None
    assert parse_quarter("2023年") is None

def test_index_roundtrip():
    assert qindex("2005Q3") == 2005 * 4 + 2
    assert qlabel(qindex("2023Q4")) == "2023Q4"
    assert qindex("2023Q1") - qindex("2022Q1") == 4

def test_qindex_rejects_bad_labels():
    with pytest.raises(ValueError):
        qindex("Q3")
    with pytest.raises(ValueError):
        qindex("")

def test_qlabel_rejects_negative_index():
    with pytest.raises(ValueError):
        qlabel(-1)
