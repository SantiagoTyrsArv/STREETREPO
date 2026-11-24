import { describe, expect, it } from "vitest";
import { fanFitScale } from "./fan";

const PHONE = { bodyWidth: 1.05, bodyHeight: 2.06, sideScale: 0.92 };

describe("fanFitScale", () => {
  it("en un lienzo ancho no achica nada", () => {
    expect(fanFitScale(0, 10, PHONE)).toBe(1);
    expect(fanFitScale(1, 10, PHONE)).toBe(1);
  });

  it("al abrirse el abanico en un lienzo angosto achica para que quepan los tres", () => {
    const closed = fanFitScale(0, 2.2, PHONE);
    const open = fanFitScale(1, 2.2, PHONE);
    expect(closed).toBe(1);
    expect(open).toBeLessThan(1);
    // Los laterales caben: media anchura necesaria × escala ≤ media anchura con margen.
    const sideHalf = 0.92 * (0.525 * Math.cos(Math.PI / 10) + 1.03 * Math.sin(Math.PI / 10));
    expect((0.58 + sideHalf) * open).toBeLessThanOrEqual((2.2 / 2) * 0.92 + 1e-9);
  });

  it("la apertura fuera de rango se acota", () => {
    expect(fanFitScale(2, 2.2, PHONE)).toBe(fanFitScale(1, 2.2, PHONE));
    expect(fanFitScale(-1, 2.2, PHONE)).toBe(fanFitScale(0, 2.2, PHONE));
  });
});
