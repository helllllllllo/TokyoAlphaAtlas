import argparse
from pathlib import Path

import duckdb

from atlas import aggregate, config, emit, ingest, normalize
from atlas.quarters import qlabel


def refresh(tx_dir=None, n02_path=None, s12_path=None, out_dir=None, db_path=None):
    db = Path(db_path or config.DB_PATH)
    db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))

    n_tx = ingest.ingest_transactions(con, src_dir=tx_dir)
    n_st = ingest.ingest_stations(con, n02_path=n02_path, s12_path=s12_path)
    print(f"ingest: {n_tx} transactions, {n_st} stations")

    report = normalize.build_clean_transactions(con)
    for k, v in report.items():
        print(f"normalize: {k} = {v}")

    asof = aggregate.asof_qidx(con)
    print(f"asof: {qlabel(asof)}")

    emit.emit_all(con, report, out_dir=out_dir)
    out = Path(out_dir or config.OUT_DIR)
    print(f"emitted artifacts to {out}")
    con.close()


def main():
    parser = argparse.ArgumentParser(prog="atlas")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("refresh", help="run the full pipeline against data/raw/")
    args = parser.parse_args()
    if args.cmd == "refresh":
        refresh()


if __name__ == "__main__":
    main()
