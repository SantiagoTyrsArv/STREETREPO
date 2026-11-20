import { describe, expect, it } from "vitest";
import { damp, magnetOffset, normalize, tiltFromPointer } from "./motion";

describe("normalize", () => {
  it("lleva la ventana a −1…1, con el centro en 0 y recortando fuera de ella", () => {
    expect(normalize(0, 0, 800, 600)).toEqual({ x: -1, y: -1 });
    expect(normalize(400, 300, 800, 600)).toEqual({ x: 0, y: 0 });
    expect(normalize(900, 700, 800, 600)).toEqual({ x: 1, y: 1 });
  });
});

describe("damp", () => {
  it("no se mueve sin tiempo y llega al objetivo con tiempo de sobra", () => {
    expect(damp(0, 10, 5, 0)).toBe(0);
    expect(damp(0, 10, 5, 10)).toBeCloseTo(10);
  });

  it("es independiente de la tasa de cuadros", () => {
    const once = damp(0, 10, 4, 1 / 30);
    const twice = damp(damp(0, 10, 4, 1 / 60), 10, 4, 1 / 60);
    expect(twice).toBeCloseTo(once, 10);
  });
});

describe("magnetOffset", () => {
  it("atrae dentro del radio, como mucho 8 px, y suelta fuera", () => {
    expect(magnetOffset(40, 0)).toEqual({ x: 4, y: 0 });
    expect(magnetOffset(0, -80)).toEqual({ x: 0, y: -8 });
    expect(magnetOffset(100, 0)).toEqual({ x: 0, y: 0 });
  });
});

describe("tiltFromPointer", () => {
  it("inclina hacia el puntero", () => {
    expect(tiltFromPointer(1, -1, 0.12)).toEqual({ rx: 0.12, ry: 0.12 });
    expect(tiltFromPointer(0, 0, 4)).toEqual({ rx: 0, ry: 0 });
  });
});
