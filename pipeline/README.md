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
    ├── hazard/liquefaction.geojson # 東京都オープンデータ（任意）
    ├── population/mesh.geojson # 国土数値情報 将来推計人口メッシュ（東京都分）
    └── landprice/L01-<year>.geojson  # 国土数値情報 L01 地価公示（年別）

## Where to download

1. **Transactions (required):** https://www.reinfolib.mlit.go.jp/ → データダウンロード →
   不動産取引価格情報 → 東京都, all periods, CSV. Unzip into `data/raw/transactions/`.
   (When the API key arrives, XPT001 can replace this manual step; contract prices
   成約価格情報 arrive the same way with `price_type` = 成約価格情報.)
2. **国土数値情報:** https://nlftp.mlit.go.jp/ksj/ → N02 (鉄道), S12 (駅別乗降客数),
   A31 (洪水浸水想定区域・東京都), A33 (土砂災害警戒区域・東京都), L01 (地価公示),
   1km将来推計人口メッシュ (東京都). Convert shapefiles to GeoJSON if needed:
   `ogr2ogr -f GeoJSON out.geojson in.shp`.
3. **Attribute names drift across vintages.** If a loader KeyErrors, check the
   downloaded file's properties and adjust the `*_ATTR` constants in `atlas/config.py`.

## Commands

    make refresh   # full pipeline → ../web/public/data/
    make test      # pytest

## Reading the run report

`refresh` prints rows in/out per stage, the station match rate (hard-fails
below 0.97 — extend ALIASES in `atlas/station_names.py` with the printed
unmatched names), counts of unparseable 建築年, and hazard/population coverage.
