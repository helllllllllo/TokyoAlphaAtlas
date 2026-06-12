import { describe, expect, it } from "vitest";
import { formatMan, formatPct, formatYen } from "./format";

describe("formatMan", () => {
  it("converts yen/m2 to 万円 with one decimal", () => {
    expect(formatMan(824000)).toBe("82.4万");
    expect(formatMan(1520000)).toBe("152.0万");
  });
  it("handles null", () => expect(formatMan(null)).toBe("—"));
});

describe("formatPct", () => {
  it("signs and rounds", () => {
    expect(formatPct(0.092)).toBe("+9.2%");
    expect(formatPct(-0.034)).toBe("−3.4%");
    expect(formatPct(0)).toBe("0.0%");
  });
  it("handles null", () => expect(formatPct(null)).toBe("—"));
});

describe("formatYen", () => {
  it("groups digits", () => expect(formatYen(33000000)).toBe("3,300万円"));
  it("handles null", () => expect(formatYen(null)).toBe("—"));
});
