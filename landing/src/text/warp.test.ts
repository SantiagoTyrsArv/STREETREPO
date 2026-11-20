import { describe, expect, it } from "vitest";
import { warpOffset } from "./warp";

describe("warpOffset", () => {
  it("lejos del puntero no deforma", () => {
    expect(warpOffset(0, 200)).toEqual({ x: 0, y: 0, skew: 0 });
  });

  it("empuja la letra alejándola del puntero, como mucho 6 px", () => {
    const right = warpOffset(10, 0); // el puntero está a la derecha de la palabra
    expect(right.x).toBeLessThan(0);
    expect(right.x).toBeGreaterThanOrEqual(-6);
    expect(warpOffset(0, -10).y).toBeGreaterThan(0);
  });

  it("es simétrico e inclina en el sentido del empuje", () => {
    expect(warpOffset(10, 0).x).toBeCloseTo(-warpOffset(-10, 0).x, 10);
    const w = warpOffset(10, 0);
    expect(w.skew).toBeCloseTo(w.x * 0.5, 10);
  });
});
