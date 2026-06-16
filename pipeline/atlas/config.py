import os
from pathlib import Path
from collections.abc import Iterable

PIPELINE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PIPELINE_DIR / "data" / "raw"
DB_PATH = PIPELINE_DIR / "data" / "atlas.duckdb"
OUT_DIR = PIPELINE_DIR.parent / "web" / "public" / "data"
API_CACHE_DIR = RAW_DIR / "api" / "xpt001"
API_GEO_CACHE_DIR = RAW_DIR / "api"
API_GEO_LAYER_DIR = RAW_DIR / "api_layers"

TOKYO_23_WARDS = [
    "千代田区", "中央区", "港区", "新宿区", "文京区", "台東区", "墨田区",
    "江東区", "品川区", "目黒区", "大田区", "世田谷区", "渋谷区", "中野区",
    "杉並区", "豊島区", "北区", "荒川区", "板橋区", "練馬区", "足立区",
    "葛飾区", "江戸川区",
]

PROPERTY_TYPES = frozenset({"中古マンション等"})
MAX_STATION_MINUTES = 15   # spec: 最寄駅距離 ≤ 15分
MIN_WINDOW_TX = 10         # trailing-4Q tx count for a valid snapshot
MIN_QUARTER_TX = 3         # tx count for a single quarterly median to exist
MIN_VOL_OBS = 6            # consecutive QoQ log-diffs needed for volatility
MAD_K = 3.5                # robust outlier threshold (modified z-score)
MATCH_RATE_GATE = 0.97     # spec §6: fail loudly below this
KNN_K = 8
TOKYO_STATION = (139.7671, 35.6812)  # lon, lat — centrality anchor
SCHEMA_VERSION = 1
API_DEFAULT_FROM = "2005Q3"
API_TILE_ZOOM = 11
API_THROTTLE_SECONDS = 0.25
API_TIMEOUT_SECONDS = 60

API_KEY_ENV_NAMES = (
    "MLIT_REAL_ESTATE_API_KEY",
    "REAL_ESTATE_LIBRARY_API_KEY",
    "MLIT_API_KEY",
)
DEFAULT_DOTENV_PATHS = (
    PIPELINE_DIR.parent / ".env",
    PIPELINE_DIR / ".env",
)

# Geo attribute names — adjust to the downloaded vintage (see pipeline/README.md)
N02_STATION_NAME = "N02_005"
N02_LINE = "N02_003"
N02_OPERATOR = "N02_004"
S12_STATION_NAME = "S12_001"
S12_RIDERSHIP = "S12_033"        # latest-year boarding count column (S12-18 vintage; update for newer files)
FLOOD_RANK_ATTR = "A31_201"      # flood depth rank property
FLOOD_RANK_ATTR_FALLBACKS = ("A31a_205", "A31_201")
FLOOD_DEPTH_WEIGHTS = {1: 0.2, 2: 0.5, 3: 0.8, 4: 1.0, 5: 1.0, 6: 1.0}
HAZARD_WEIGHTS = {
    "flood": 0.45,
    "landslide": 0.20,
    "liquefaction": 0.15,
    "embankment": 0.10,
    "danger_zone": 0.10,
}
POP_BASE_ATTR = "PTN_2025"
POP_FUTURE_ATTR = "PTN_2045"
REGION_LABEL = "Greater Tokyo"
REGION_BBOX = (139.0, 35.3, 140.25, 36.2)  # lon_min, lat_min, lon_max, lat_max — Tokyo core plus Saitama/Kawasaki commuter belt
TOKYO_BBOX = REGION_BBOX  # backwards-compatible alias for older call sites/tests
LEGACY_TEXT_MUNICIPALITIES = frozenset(TOKYO_23_WARDS)
SAME_NAME_MERGE_RADIUS_KM = 10  # same-name members farther than this become line-suffixed stations instead of being merged
LANDPRICE_PRICE_ATTR = "L01_006"
LANDPRICE_PRICE_ATTR_BY_YEAR = {2024: "L01_008"}  # L01-2024 moved price from L01_006 → L01_008
METRIC_CRS = 6677                # JGD2011 Plane Rectangular CS IX (Tokyo)
STATION_BUFFER_M = 800           # hazard buffer
POP_BUFFER_M = 1000              # population buffer

HIST_WINDOW_QUARTERS = 8
HIST_MIN_TX = 20
HIST_BINS = 12

def _dotenv_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out

def get_mlit_api_key(dotenv_paths: Iterable[Path] | None = None) -> str | None:
    """Return the local MLIT 不動産情報ライブラリ API key without hard-coding it."""
    for name in API_KEY_ENV_NAMES:
        value = os.getenv(name)
        if value:
            return value.strip()

    for path in dotenv_paths if dotenv_paths is not None else DEFAULT_DOTENV_PATHS:
        values = _dotenv_values(Path(path))
        for name in API_KEY_ENV_NAMES:
            value = values.get(name)
            if value:
                return value.strip()
    return None
