import { describe, expect, it } from "vitest";
import { parseWeight, sumHundredths, toHundredths } from "./parseWeight";

describe("parseWeight", () => {
  it.each([
    ["0,5", "0.50"],
    ["0.30", "0.30"],
    ["1", "1.00"],
    ["0", "0.00"],
    [" 0,25 ", "0.25"],
    ["1,00", "1.00"],
  ])("%s → %s", (text, expected) => {
    expect(parseWeight(text)).toBe(expected);
  });

  it.each(["0,505", "-0.1", "1.01", "abc", "", "0,", ",5", "1e-1", "0,5,0", "2"])(
    "rechaza «%s»",
    (text) => {
      expect(parseWeight(text)).toBeNull();
    },
  );
});

describe("suma en centésimas", () => {
  it("convierte a enteros para no sumar con decimales binarios", () => {
    expect(toHundredths("0,1")).toBe(10);
    expect(toHundredths("0,07")).toBe(7);
    expect(toHundredths("0,505")).toBeNull();
  });

  it("0,1 + 0,2 + 0,7 suma exactamente 1,00", () => {
    expect(sumHundredths(["0,1", "0,2", "0,7"])).toBe(100);
  });

  it("0,50 + 0,30 + 0,19 suma 0,99", () => {
    expect(sumHundredths(["0,50", "0,30", "0,19"])).toBe(99);
  });

  it("sin suma si algún peso no es válido", () => {
    expect(sumHundredths(["0,5", "abc", "0,2"])).toBeNull();
  });
});
