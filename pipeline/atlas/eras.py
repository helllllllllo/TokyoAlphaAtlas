import re

ERA_STARTS = {"明治": 1868, "大正": 1912, "昭和": 1926, "平成": 1989, "令和": 2019}
_ERA_RE = re.compile(r"(明治|大正|昭和|平成|令和)(元|\d+)年")
_SEIREKI_RE = re.compile(r"(\d{4})年")


def to_year(text):
    """建築年 text (和暦 or 西暦) -> int year, or None if unparseable."""
    if not isinstance(text, str) or not text:
        return None
    m = _SEIREKI_RE.search(text)
    if m:
        return int(m.group(1))
    m = _ERA_RE.search(text)
    if m:
        n = 1 if m.group(2) == "元" else int(m.group(2))
        return ERA_STARTS[m.group(1)] + n - 1
    return None
