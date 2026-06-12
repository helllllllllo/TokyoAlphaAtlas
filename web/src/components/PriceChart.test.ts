import { describe, expect, it } from "vitest";
import { chartRows } from "./PriceChart";

describe("chartRows", () => {
  it("merges median series with landprice by year", () => {
    const rows = chartRows(
      { quarters: ["2023Q3", "2023Q4"], median_ppsm: [500000, 660000], tx_count: [3, 5] },
      { years: [2023], price: [800000] },
    );
    expect(rows).toHaveLength(2);
    expect(rows[0]).toEqual({ q: "2023Q3", median: 500000, landprice: 800000 });
    expect(rows[1].landprice).toBeNull(); // landprice only plotted on Q3 of its year
  });
  it("handles null medians and missing landprice", () => {
    const rows = chartRows(
      { quarters: ["2023Q4"], median_ppsm: [null], tx_count: [0] },
      null,
    );
    expect(rows[0]).toEqual({ q: "2023Q4", median: null, landprice: null });
  });
});
