import { describe, expect, it } from "vitest";
import { MASK_UNTIL, letterFill, maskScale } from "./heroMaskScale";

describe("maskScale", () => {
  it("parte de 1 y atraviesa las letras (≥ 40) al final del tramo", () => {
    expect(maskScale(0)).toBe(1);
    expect(maskScale(MASK_UNTIL)).toBeGreaterThanOrEqual(40);
    expect(maskScale(0.9)).toBe(maskScale(MASK_UNTIL));
  });

  it("crece sin retroceder, despacio al principio", () => {
    const values = [0, 0.25, 0.5, 0.75, 1].map((f) => maskScale(f * MASK_UNTIL));
    for (let i = 1; i < values.length; i++) {
      expect(values[i]).toBeGreaterThan(values[i - 1] as number);
    }
    expect(maskScale(MASK_UNTIL / 3)).toBeLessThan(3);
  });

  it("el tramo del zoom ocupa casi la mitad de la reproducción de la portada", () => {
    expect(MASK_UNTIL).toBe(0.45);
  });
});

describe("letterFill", () => {
  it("las letras empiezan con todo su color", () => {
    expect(letterFill(0)).toBe(1);
  });

  it("el color se desvanece mientras avanza el zoom", () => {
    const values = [0, 0.25, 0.5, 0.75].map((f) => letterFill(f * MASK_UNTIL));
    for (let i = 1; i < values.length; i++) {
      expect(values[i]).toBeLessThan(values[i - 1] as number);
    }
  });

  it("al terminar el zoom ya no hay color: se ve la escena", () => {
    expect(letterFill(MASK_UNTIL)).toBe(0);
    expect(letterFill(1)).toBe(0);
  });
});
