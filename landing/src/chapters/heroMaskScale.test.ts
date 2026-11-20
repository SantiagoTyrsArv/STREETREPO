import { describe, expect, it } from "vitest";
import { maskScale } from "./heroMaskScale";

describe("maskScale", () => {
  it("parte de 1 y atraviesa las letras (≥ 40) al final del tramo", () => {
    expect(maskScale(0)).toBe(1);
    expect(maskScale(0.3)).toBeGreaterThanOrEqual(40);
    expect(maskScale(0.5)).toBe(maskScale(0.3));
  });

  it("crece sin retroceder, despacio al principio", () => {
    const values = [0, 0.1, 0.2, 0.3].map((p) => maskScale(p));
    for (let i = 1; i < values.length; i++) {
      expect(values[i]).toBeGreaterThan(values[i - 1] as number);
    }
    expect(maskScale(0.1)).toBeLessThan(3);
  });
});
