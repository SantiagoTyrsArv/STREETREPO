import { describe, expect, it } from "vitest";
import { dominantAccent, hexToRgb, mixRgb, paletteFor, type Rgb } from "./palette";

const T = {
  night: hexToRgb("#0a0e13"),
  ink: hexToRgb("#1b2430"),
  amber: hexToRgb("#f5b800"),
  signal: hexToRgb("#4c8dff"),
  repair: hexToRgb("#3dd68c"),
};

describe("hexToRgb", () => {
  it("convierte a 0–1", () => {
    const c = hexToRgb("#4c8dff");
    expect(c[0]).toBeCloseTo(0.298, 3);
    expect(c[1]).toBeCloseTo(0.553, 3);
    expect(c[2]).toBe(1);
  });

  it("acepta mayúsculas y espacios del valor de una variable CSS", () => {
    expect(hexToRgb(" #FFFFFF")).toEqual([1, 1, 1]);
  });

  it("rechaza lo que no es un color de 6 cifras", () => {
    expect(() => hexToRgb("red")).toThrow();
  });
});

describe("mixRgb", () => {
  it("interpola canal a canal", () => {
    expect(mixRgb([0, 0, 0], [1, 1, 1], 0.25)).toEqual([0.25, 0.25, 0.25]);
  });
});

describe("paletteFor", () => {
  it("parte de la noche y la tinta y añade el acento en dos intensidades", () => {
    const p = paletteFor("repair", T);
    expect(p[0]).toEqual(T.night);
    expect(p[1]).toEqual(T.ink);
    expect(p[2]).toEqual(mixRgb(T.ink, T.repair, 0.22));
    expect(p[3]).toEqual(mixRgb(T.night, T.repair, 0.5));
  });

  it("sin acento usa un azul muy tenue", () => {
    const p = paletteFor("none", T);
    expect(p[2]).toEqual(mixRgb(T.ink, T.signal, 0.12));
    expect(p[3]).toEqual(mixRgb(T.night, T.signal, 0.3));
  });
});

describe("dominantAccent", () => {
  it("elige la sección que más ocupa la pantalla", () => {
    expect(
      dominantAccent([
        { accent: "amber", ratio: 0.2 },
        { accent: "signal", ratio: 0.7 },
      ]),
    ).toBe("signal");
  });

  it("sin nada visible no hay acento", () => {
    expect(dominantAccent([])).toBe("none");
    expect(dominantAccent([{ accent: "amber", ratio: 0 }])).toBe("none");
  });
});

// Garantiza que el tipo exportado sea una tupla de tres canales.
const sample: Rgb = [0, 0, 0];
void sample;
