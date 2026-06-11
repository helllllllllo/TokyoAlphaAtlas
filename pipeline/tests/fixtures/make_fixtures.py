"""Deterministically (re)generate the cp932 transaction CSV fixture.
Run from pipeline/:  uv run python tests/fixtures/make_fixtures.py
"""
import csv
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "transactions"
OUT.mkdir(exist_ok=True)

HEADERS = ["種類", "市区町村名", "地区名", "最寄駅：名称", "最寄駅：距離（分）",
           "取引価格（総額）", "面積（㎡）", "建築年", "取引時期"]

# (station, ward, ppsm) — 3 tx per quarter at ppsm*0.9, ppsm, ppsm*1.1 on 50㎡
STATIONS = [("中野", "中野区"), ("高円寺", "杉並区"), ("新宿テスト", "新宿区")]
PPSM = {"中野": {2022: 600_000, 2023: 660_000},
        "高円寺": {2022: 500_000, 2023: 500_000},
        "新宿テスト": {2022: 1_000_000, 2023: 1_000_000}}

rows = []
for year in (2022, 2023):
    for q in (1, 2, 3, 4):
        period = f"{year}年第{q}四半期"
        for st, ward in STATIONS:
            base = PPSM[st][year]
            for mult in (0.9, 1.0, 1.1):
                price = int(base * mult * 50)
                rows.append(["中古マンション等", ward, "テスト町", st, "5",
                             str(price), "50", "平成2年", period])

# dirty rows that the normalize stage must drop
rows += [
    ["宅地(土地と建物)", "中野区", "x", "中野", "5", "30000000", "50", "平成2年", "2023年第4四半期"],
    ["中古マンション等", "横浜市西区", "x", "横浜", "5", "30000000", "50", "平成2年", "2023年第4四半期"],
    ["中古マンション等", "中野区", "x", "中野", "30分?60分", "30000000", "50", "平成2年", "2023年第4四半期"],
    ["中古マンション等", "中野区", "x", "中野", "5", "30000000", "50", "不明", "2023年第4四半期"],
    ["中古マンション等", "中野区", "x", "中野", "5", "990000000", "50", "平成2年", "2023年第4四半期"],  # MAD outlier (ppsm 19.8M)
    ["中古マンション等", "葛飾区", "x", "存在しない駅", "5", "25000000", "50", "平成2年", "2023年第4四半期"],
    # real-world blank cells (csv writes "" as an empty cell; pandas dtype=str reads it as NaN)
    ["中古マンション等", "中野区", "x", "中野", "5", "30000000", "50", "", "2023年第4四半期"],   # blank 建築年 — survives, built_year=None
    ["中古マンション等", "中野区", "x", "", "5", "30000000", "50", "平成2年", "2023年第4四半期"],  # blank 最寄駅：名称 — dropped as no_station
    ["中古マンション等", "中野区", "x", "中野", "5", "30000000", "50", "平成2年", ""],            # blank 取引時期 — quarter=None, dropped
]

with open(OUT / "tx_fixture.csv", "w", encoding="cp932", newline="") as f:
    w = csv.writer(f)
    w.writerow(HEADERS)
    w.writerows(rows)
print(f"wrote {len(rows)} rows")
