import argparse
from datetime import date
from pathlib import Path

import duckdb

from atlas import (
    aggregate, api_geo, config, emit, hazard, ingest, landprice, normalize,
    population, redevelopment,
)
from atlas.quarters import qlabel


def current_quarter_label(today: date | None = None) -> str:
    d = today or date.today()
    return f"{d.year}Q{((d.month - 1) // 3) + 1}"


def refresh(tx_dir=None, n02_path=None, s12_path=None, out_dir=None, db_path=None,
            hazard_dir=None, population_path=None, landprice_dir=None,
            redevelopment_dir=None, rail_src=None, emit_hazard_dir=None,
            emit_redevelopment_dir=None, tx_source="csv", geo_source="local",
            api_from=None, api_to=None, api_cache_dir=None, api_force=False,
            api_price_classification=None, api_chunk_quarters=4,
            api_tile_zoom=config.API_TILE_ZOOM, api_geo_force=False,
            api_geo_zoom=None):
    db = Path(db_path or config.DB_PATH)
    db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    try:
        if tx_source == "api":
            kwargs = {
                "from_period": api_from or config.API_DEFAULT_FROM,
                "to_period": api_to or current_quarter_label(),
            }
            if api_cache_dir is not None:
                kwargs["cache_dir"] = Path(api_cache_dir)
            if api_force:
                kwargs["force"] = True
            if api_price_classification is not None:
                kwargs["price_classification"] = api_price_classification
            if api_chunk_quarters != 4:
                kwargs["chunk_quarters"] = api_chunk_quarters
            if api_tile_zoom != config.API_TILE_ZOOM:
                kwargs["tiles"] = ingest.tiles_for_bbox(z=api_tile_zoom)
            n_tx = ingest.ingest_transactions_api(con, **kwargs)
        else:
            n_tx = ingest.ingest_transactions(con, src_dir=tx_dir)
        n_st = ingest.ingest_stations(con, n02_path=n02_path, s12_path=s12_path)
        print(f"ingest: {n_tx} transactions, {n_st} stations")

        geo_sources = None
        if geo_source == "api":
            geo_sources = api_geo.prepare_api_geo_sources(
                force=api_geo_force,
                default_zoom=api_geo_zoom,
            )
            _hz_dir = geo_sources.hazard_dir
            _population_path = geo_sources.population_path
            _landprice_dir = geo_sources.landprice_dir
            _redevelopment_dir = geo_sources.redevelopment_dir
            _emit_hz_dir = geo_sources.overlay_hazard_dir
            _emit_redev_dir = geo_sources.overlay_redevelopment_dir
        elif geo_source == "none":
            missing = db.parent / "__missing_geo__"
            _hz_dir = missing / "hazard"
            _population_path = missing / "population.geojson"
            _landprice_dir = missing / "landprice"
            _redevelopment_dir = missing / "redevelopment"
            _emit_hz_dir = None
            _emit_redev_dir = None
        else:
            _hz_dir = Path(hazard_dir) if hazard_dir else config.RAW_DIR / "hazard"
            _population_path = population_path
            _landprice_dir = landprice_dir
            _redevelopment_dir = Path(redevelopment_dir) if redevelopment_dir else config.RAW_DIR / "redevelopment"
            _emit_hz_dir = emit_hazard_dir or hazard_dir
            _emit_redev_dir = emit_redevelopment_dir or redevelopment_dir

        stations_df = con.execute("select * from stations").df()
        stations_df = hazard.add_hazard(
            stations_df,
            flood_path=_hz_dir / "flood.geojson",
            landslide_path=_hz_dir / "landslide.geojson",
            liquefaction_path=_hz_dir / "liquefaction.geojson",
            embankment_path=_hz_dir / "embankment.geojson",
            danger_zone_path=_hz_dir / "danger_zone.geojson",
        )
        stations_df = population.add_population(stations_df, mesh_path=_population_path)
        stations_df = landprice.add_landprice(stations_df, src_dir=_landprice_dir)
        stations_df = redevelopment.add_redevelopment(stations_df, src_dir=_redevelopment_dir)
        con.register("_sth", stations_df)
        con.execute("create or replace table stations as select * from _sth")
        con.unregister("_sth")
        n_stations = len(stations_df)
        risk_scored = int(stations_df.hazard_score.notna().sum())
        pop_scored = int(stations_df.pop_change.notna().sum())
        redevelopment_scored = int(stations_df.redevelopment_score.notna().sum())
        print(f"hazard: scored {risk_scored}/{n_stations} stations")
        print(f"population: scored {pop_scored}/{n_stations} stations")
        print(f"redevelopment: scored {redevelopment_scored}/{n_stations} stations")
        if geo_sources is not None:
            print(f"api cache: tiles {geo_sources.tiles_fetched}")
            for label, count in (
                ("risk", risk_scored),
                ("population", pop_scored),
                ("redevelopment", redevelopment_scored),
            ):
                if n_stations and count / n_stations < 0.8:
                    print(f"warning: {label} API coverage below 80% ({count}/{n_stations})")

        report = normalize.build_clean_transactions(con)
        for k, v in report.items():
            print(f"normalize: {k} = {v}")

        asof = aggregate.asof_qidx(con)
        print(f"asof: {qlabel(asof)}")

        emit.emit_all(con, report, out_dir=out_dir,
                      rail_src=rail_src,
                      hazard_dir=_emit_hz_dir,
                      redevelopment_dir=_emit_redev_dir,
                      api_cache_tiles=0 if geo_sources is None else geo_sources.tiles_fetched)
        out = Path(out_dir or config.OUT_DIR)
        print(f"emitted artifacts to {out}")
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(prog="atlas")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_refresh = sub.add_parser("refresh", help="run the full pipeline against data/raw/")
    p_refresh.add_argument("--tx-source", choices=["csv", "api"], default="csv",
                           help="transaction source: local CSVs or MLIT XPT001 API")
    p_refresh.add_argument("--geo-source", choices=["api", "local", "none"], default=None,
                           help="geo enrichment source: default is api when an MLIT key is configured, else local")
    p_refresh.add_argument("--tx-dir", type=Path, default=None,
                           help="transaction CSV directory (default: data/raw/transactions)")
    p_refresh.add_argument("--api-from", default=config.API_DEFAULT_FROM,
                           help="API start quarter, e.g. 2005Q3")
    p_refresh.add_argument("--api-to", default=None,
                           help="API end quarter, e.g. 2025Q4 (default: current calendar quarter)")
    p_refresh.add_argument("--api-cache-dir", type=Path, default=None,
                           help=f"XPT001 GeoJSON cache directory (default: {config.API_CACHE_DIR})")
    p_refresh.add_argument("--api-force", action="store_true",
                           help="re-fetch API tiles even when cached")
    p_refresh.add_argument("--api-price-classification", choices=["01", "02"], default=None,
                           help="01=transaction prices only, 02=contract prices only, unset=both")
    p_refresh.add_argument("--api-chunk-quarters", type=int, default=4,
                           help="quarters per XPT001 tile request")
    p_refresh.add_argument("--api-tile-zoom", type=int, default=config.API_TILE_ZOOM,
                           help="XPT001 tile zoom; 11 is broad and minimizes requests")
    p_refresh.add_argument("--api-geo-force", action="store_true",
                           help="re-fetch XKT/XPT geo API tiles even when cached")
    p_refresh.add_argument("--api-geo-zoom", type=int, default=None,
                           help="default XKT geo tile zoom; flood remains z14 and land price remains z13")
    p_refresh.add_argument("--n02", type=Path, default=None,
                           help="N02 stations GeoJSON path (default: data/raw/n02/...)")
    p_refresh.add_argument("--s12", type=Path, default=None,
                           help="S12 ridership GeoJSON path (default: data/raw/s12/...)")
    p_refresh.add_argument("--out-dir", type=Path, default=None,
                           help=f"artifact output directory (default: {config.OUT_DIR})")
    p_refresh.add_argument("--db-path", type=Path, default=None,
                           help=f"DuckDB working store path (default: {config.DB_PATH})")
    p_refresh.add_argument("--hazard-dir", type=Path, default=None,
                           help="hazard source directory (default: data/raw/hazard)")
    p_refresh.add_argument("--population", "--population-path", dest="population",
                           type=Path, default=None,
                           help="population mesh GeoJSON path (default: data/raw/population/mesh.geojson)")
    p_refresh.add_argument("--landprice-dir", type=Path, default=None,
                           help="land price source directory (default: data/raw/landprice)")
    p_refresh.add_argument("--redevelopment-dir", type=Path, default=None,
                           help="redevelopment source directory (default: data/raw/redevelopment)")
    p_refresh.add_argument("--rail-src", type=Path, default=None,
                           help="rail sections GeoJSON path (default: data/raw/n02/rail_sections.geojson)")
    p_refresh.add_argument("--emit-hazard-dir", type=Path, default=None,
                           help="hazard overlay output directory (defaults to --hazard-dir)")
    p_refresh.add_argument("--emit-redevelopment-dir", type=Path, default=None,
                           help="redevelopment overlay output directory (defaults to --redevelopment-dir)")
    args = parser.parse_args()
    if args.cmd == "refresh":
        refresh(
            tx_dir=args.tx_dir,
            n02_path=args.n02,
            s12_path=args.s12,
            out_dir=args.out_dir,
            db_path=args.db_path,
            hazard_dir=args.hazard_dir,
            population_path=args.population,
            landprice_dir=args.landprice_dir,
            redevelopment_dir=args.redevelopment_dir,
            rail_src=args.rail_src,
            emit_hazard_dir=args.emit_hazard_dir,
            emit_redevelopment_dir=args.emit_redevelopment_dir,
            tx_source=args.tx_source,
            geo_source=args.geo_source or ("api" if config.get_mlit_api_key() else "local"),
            api_from=args.api_from,
            api_to=args.api_to,
            api_cache_dir=args.api_cache_dir,
            api_force=args.api_force,
            api_price_classification=args.api_price_classification,
            api_chunk_quarters=args.api_chunk_quarters,
            api_tile_zoom=args.api_tile_zoom,
            api_geo_force=args.api_geo_force,
            api_geo_zoom=args.api_geo_zoom,
        )


if __name__ == "__main__":
    main()
