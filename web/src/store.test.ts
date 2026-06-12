import { beforeEach, describe, expect, it } from "vitest";
import { useApp } from "./store";

beforeEach(() => {
  useApp.setState({
    lens: "price", quarterIdx: null, selectedId: null, compare: [null, null],
  });
});

describe("store", () => {
  it("switching lens away from price resets the quarter scrub", () => {
    useApp.getState().setQuarter(10);
    useApp.getState().setLens("momentum");
    expect(useApp.getState().quarterIdx).toBeNull();
  });
  it("addCompare fills slots then rotates", () => {
    const s = useApp.getState();
    s.addCompare("A");
    s.addCompare("B");
    s.addCompare("C");
    expect(useApp.getState().compare).toEqual(["B", "C"]);
  });
  it("addCompare ignores duplicates", () => {
    useApp.getState().addCompare("A");
    useApp.getState().addCompare("A");
    expect(useApp.getState().compare).toEqual(["A", null]);
  });
});
