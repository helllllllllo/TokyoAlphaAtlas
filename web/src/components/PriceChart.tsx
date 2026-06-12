import {
  Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { formatMan } from "../lib/format";
import type { StationDetail } from "../types";

export interface ChartRow {
  q: string;
  median: number | null;
  landprice: number | null;
}

/** Land price is yearly — plot it on the Q3 tick of its year (地価公示 is as of Jan 1; Q3 keeps it mid-series visually distinct). */
export function chartRows(
  series: StationDetail["series"],
  landprice: StationDetail["landprice"],
): ChartRow[] {
  const byYear = new Map<number, number>();
  landprice?.years.forEach((y, i) => byYear.set(y, landprice.price[i]));
  return series.quarters.map((q, i) => ({
    q,
    median: series.median_ppsm[i],
    landprice: q.endsWith("Q3") ? (byYear.get(Number(q.slice(0, 4))) ?? null) : null,
  }));
}

export function PriceChart({ detail }: { detail: StationDetail }) {
  const rows = chartRows(detail.series, detail.landprice);
  return (
    <div style={{ height: 150 }}>
      <ResponsiveContainer>
        <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <XAxis dataKey="q" tick={{ fontSize: 9, fill: "#7a8ab8" }} interval="preserveStartEnd" />
          <YAxis tickFormatter={v => formatMan(v as number)} tick={{ fontSize: 9, fill: "#7a8ab8" }} width={44} />
          <Tooltip
            contentStyle={{ background: "#0d1426", border: "1px solid #1a2440", fontSize: 11 }}
            formatter={(v: number) => `${formatMan(v)}円`}
          />
          <Line dataKey="median" name="㎡単価" stroke="#c9a86a" dot={false} strokeWidth={2} connectNulls />
          <Line dataKey="landprice" name="地価公示" stroke="#5f8fe0" strokeDasharray="5 4" dot={{ r: 2 }} connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
