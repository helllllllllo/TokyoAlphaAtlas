import argparse
from pathlib import Path

import duckdb
import pandas as pd

from atlas import aggregate, config, emit, hazard, ingest, normalize, population
from atlas.quarters import qlabel


def refresh(tx_dir=None, n02_path=None, s12_path=None, out_dir=None, db_path=None):
    db = Path(db_path or config.DB_PATH)
    db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    try:
        n_tx = ingest.ingest_transactions(con, src_dir=tx_dir)
        n_st = ingest.ingest_stations(con, n02_path=n02_path, s12_path=s12_path)
        print(f"ingest: {n_tx} transactions, {n_st} stations")

        stations_df = con.execute("select * from stations").df()
        stations_df = hazard.add_hazard(stations_df)
        stations_df = population.add_population(stations_df)
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

        emit.emit_all(con, report, out_dir=out_dir)
        out = Path(out_dir or config.OUT_DIR)
        print(f"emitted artifacts to {out}")
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(prog="atlas")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_refresh = sub.add_parser("refresh", help="run the full pipeline against data/raw/")
    p_refresh.add_argument("--out-dir", type=Path, default=None,
                           help=f"artifact output directory (default: {config.OUT_DIR})")
    p_refresh.add_argument("--db-path", type=Path, default=None,
                           help=f"DuckDB working store path (default: {config.DB_PATH})")
    args = parser.parse_args()
    if args.cmd == "refresh":
        refresh(out_dir=args.out_dir, db_path=args.db_path)


if __name__ == "__main__":
    main()
