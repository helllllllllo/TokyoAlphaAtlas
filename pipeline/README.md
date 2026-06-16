# Atlas pipeline

Run everything from this directory. `make refresh` expects raw data laid out as below;
every geo source is optional — missing ones degrade to `null` in the artifacts.

## Raw data layout

    data/raw/
    ├── transactions/*.csv      # REQUIRED — MLIT 不動産取引価格情報 quarterly CSVs
    ├── n02/stations.geojson    # 国土数値情報 N02 鉄道（駅）
    ├── n02/rail_sections.geojson  # 国土数値情報 N02 鉄道（路線）
    ├── s12/ridership.geojson   # 国土数値情報 S12 駅別乗降客数
    ├── hazard/flood.geojson    # 国土数値情報 A31 洪水浸水想定区域
    ├── hazard/landslide.geojson    # 国土数値情報 A33 土砂災害警戒区域
    ├── hazard/liquefaction.geojson # 自治体オープンデータ（任意）
    ├── population/mesh.geojson # 国土数値情報 将来推計人口メッシュ（対象地域分）
    └── landprice/L01-<year>.geojson  # 国土数値情報 L01 地価公示（年別）

## Where to download

1. **Transactions (required):** https://www.reinfolib.mlit.go.jp/ → データダウンロード →
   不動産取引価格情報 → 対象地域, all periods, CSV. Unzip into `data/raw/transactions/`.
   API-backed ingestion can use `MLIT_REAL_ESTATE_API_KEY` from the shell,
   repo-root `.env`, or `pipeline/.env`. Contract prices 成約価格情報 should carry
   `price_type` = 成約価格情報 when that loader is enabled.
2. **国土数値情報:** https://nlftp.mlit.go.jp/ksj/ → N02 (鉄道), S12 (駅別乗降客数),
   A31 (洪水浸水想定区域), A33 (土砂災害警戒区域), L01 (地価公示),
   1km将来推計人口メッシュ. Convert shapefiles to GeoJSON if needed:
   `ogr2ogr -f GeoJSON out.geojson in.shp`.
3. **Attribute names drift across vintages.** If a loader KeyErrors, check the
   downloaded file's properties and adjust the `*_ATTR` constants in `atlas/config.py`.

## Commands

    make refresh   # full pipeline → ../web/public/data/
    make test      # pytest

API-backed transaction refresh:

    uv run python -m atlas.cli refresh --tx-source api --api-from 2005Q3 --api-to 2025Q4

Useful narrower runs:

    # contract prices only, available from 2021Q1
    uv run python -m atlas.cli refresh --tx-source api --api-from 2021Q1 --api-to 2025Q4 --api-price-classification 02

    # transaction prices only
    uv run python -m atlas.cli refresh --tx-source api --api-from 2005Q3 --api-to 2025Q4 --api-price-classification 01

API responses are cached in `data/raw/api/xpt001/` so interrupted runs can resume.

## Local API key

Copy `pipeline/.env.example` to either repo-root `.env` or `pipeline/.env`, then set:

    MLIT_REAL_ESTATE_API_KEY=...

Accepted aliases are `REAL_ESTATE_LIBRARY_API_KEY` and `MLIT_API_KEY`. Real `.env`
files are gitignored.

## Reading the run report

`refresh` prints rows in/out per stage, the station match rate (hard-fails
below 0.97 — extend ALIASES in `atlas/station_names.py` with the printed
unmatched names), counts of unparseable 建築年, and hazard/population coverage.
