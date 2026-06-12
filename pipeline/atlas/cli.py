import argparse
from pathlib import Path

import duckdb

from atlas import aggregate, config, emit, hazard, ingest, landprice, normalize, population
from atlas.quarters import qlabel


def refresh(tx_dir=None, n02_path=None, s12_path=None, out_dir=None, db_path=None,
            hazard_dir=None, population_path=None, landprice_dir=None,
            rail_src=None, emit_hazard_dir=None):
    db = Path(db_path or config.DB_PATH)
    db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    try:
        n_tx = ingest.ingest_transactions(con, src_dir=tx_dir)
        n_st = ingest.ingest_stations(con, n02_path=n02_path, s12_path=s12_path)
        print(f"ingest: {n_tx} transactions, {n_st} stations")

        stations_df = con.execute("select * from stations").df()
        _hz_dir = Path(hazard_dir) if hazard_dir else config.RAW_DIR / "hazard"
        stations_df = hazard.add_hazard(
            stations_df,
            flood_path=_hz_dir / "flood.geojson",
            landslide_path=_hz_dir / "landslide.geojson",
            liquefaction_path=_hz_dir / "liquefaction.geojson",
        )
        stations_df = population.add_population(stations_df, mesh_path=population_path)
        stations_df = landprice.add_landprice(stations_df, src_dir=landprice_dir)
        con.register("_sth", stations_df)
        con.execute("create or replace table stations as select * from _sth")
        con.unregister("_sth")
        print(f"hazard: scored {int(stations_df.hazard_score.notna().sum())}/{len(stations_df)} stations")
        print(f"population: scored {int(stations_df.pop_change.notna().sum())}/{len(stations_df)} stations")

        report = normalize.build_clean_transactions(con)
        for k, v in report.items():
            print(f"normalize: {k} = {v}")

        asof = aggregate.asof_qidx(con)
        print(f"asof: {qlabel(asof)}")

        # emit_hazard_dir defaults to same hazard_dir used for scoring
        _emit_hz_dir = emit_hazard_dir or hazard_dir
        emit.emit_all(con, report, out_dir=out_dir,
                      rail_src=rail_src,
                      hazard_dir=_emit_hz_dir)
        out = Path(out_dir or config.OUT_DIR)
        print(f"emitted artifacts to {out}")
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(prog="atlas")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_refresh = sub.add_parser("refresh", help="run the full pipeline against data/raw/")
    p_refresh.add_argument("--tx-dir", type=Path, default=None,
                           help="transaction CSV directory (default: data/raw/transactions)")
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
    p_refresh.add_argument("--population", type=Path, default=None,
                           help="population mesh GeoJSON path (default: data/raw/population/mesh.geojson)")
    p_refresh.add_argument("--landprice-dir", type=Path, default=None,
                           help="land price source directory (default: data/raw/landprice)")
    p_refresh.add_argument("--rail-src", type=Path, default=None,
                           help="rail sections GeoJSON path (default: data/raw/n02/rail_sections.geojson)")
    p_refresh.add_argument("--emit-hazard-dir", type=Path, default=None,
                           help="hazard overlay output directory (defaults to --hazard-dir)")
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
            rail_src=args.rail_src,
            emit_hazard_dir=args.emit_hazard_dir,
        )


if __name__ == "__main__":
    main()
