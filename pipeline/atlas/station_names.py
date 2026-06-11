import re
import unicodedata

# Normalized-but-still-mismatched name -> canonical N02 name.
# Extend this table when the normalize stage's unmatched report flags names.
ALIASES: dict[str, str] = {}

_PAREN_RE = re.compile(r"[（(].*?[)）]")


def normalize(name):
    """Normalize a station name for joining transaction CSVs to N02 geometry."""
    if not name:
        return ""
    s = unicodedata.normalize("NFKC", name).strip()
    s = _PAREN_RE.sub("", s)
    s = s.replace("ケ", "ヶ")
    s = s.removesuffix("駅")
    return ALIASES.get(s, s)
