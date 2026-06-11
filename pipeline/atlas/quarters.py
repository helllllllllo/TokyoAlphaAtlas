import re

from atlas.eras import ERA_STARTS

_Q_RE = re.compile(r"(?:(\d{4})|(明治|大正|昭和|平成|令和)(元|\d+))年第([1-4１-４])四半期")
_Z2H = str.maketrans("１２３４", "1234")
_QLABEL_RE = re.compile(r"^\d{4}Q[1-4]$")


def parse_quarter(text):
    """'2023年第３四半期' / '平成25年第１四半期' -> '2023Q3'; None if unparseable."""
    if not isinstance(text, str):
        return None
    m = _Q_RE.search(text)
    if not m:
        return None
    if m.group(1):
        year = int(m.group(1))
    else:
        n = 1 if m.group(3) == "元" else int(m.group(3))
        year = ERA_STARTS[m.group(2)] + n - 1
    q = int(m.group(4).translate(_Z2H))
    return f"{year}Q{q}"


def qindex(q):
    """'2023Q3' -> monotonic int for window arithmetic."""
    if not q or not _QLABEL_RE.match(q):
        raise ValueError(f"not a quarter label: {q!r}")
    return int(q[:4]) * 4 + int(q[5]) - 1


def qlabel(i):
    """Inverse of qindex: monotonic int -> 'YYYYQn' label."""
    if i < 0:
        raise ValueError(f"negative quarter index: {i}")
    return f"{i // 4}Q{i % 4 + 1}"
