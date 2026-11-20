import { describe, expect, it } from "vitest";
import { flowScore, formatDecimal, proximityScore, severityScore, urgency } from "./urgency";

describe("reglas de normalización (guía 2.2)", () => {
  it("severidad y jerarquía vial", () => {
    expect([severityScore("baja"), severityScore("media"), severityScore("alta")]).toEqual([
      3, 6, 10,
    ]);
    expect(
      (["principal", "secundaria", "terciaria", "residencial", "sin-via"] as const).map(flowScore),
    ).toEqual([10, 7, 5, 2, 2]);
  });

  it("proximidad: 10 hasta 100 m, lineal hasta 0 a 500 m, con la distancia en centímetros", () => {
    expect(proximityScore(100)).toBe(10);
    expect(proximityScore(500)).toBe(0);
    expect(proximityScore(350)).toBe(3.75);
    expect(proximityScore(600)).toBe(0);
    expect(proximityScore(100.004)).toBe(10);
    expect(proximityScore(180)).toBe(8);
  });
});

describe("urgency (tabla de la guía 8.3)", () => {
  it.each([
    [{ s: 10, f: 7, p: 8 }, 8.7],
    [{ s: 6, f: 10, p: 10 }, 8],
    [{ s: 10, f: 5, p: 3.75 }, 7.25],
    [{ s: 6, f: 5, p: 10 }, 6.5],
    [{ s: 6, f: 7, p: 5 }, 6.1],
    [{ s: 6, f: 2, p: 0 }, 3.6],
  ])("%o → %d", (scores, expected) => {
    expect(urgency(scores)).toBe(expected);
  });

  it("redondea a dos decimales, mitad hacia arriba", () => {
    // 0,5·3 + 0,3·2 + 0,2·0,05 = 2,11 exactos; 0,2·0,25 = 0,05 → 2,15.
    expect(urgency({ s: 3, f: 2, p: 0.25 })).toBe(2.15);
  });
});

describe("formatDecimal", () => {
  it("usa coma y dos cifras", () => {
    expect(formatDecimal(8.7)).toBe("8,70");
    expect(formatDecimal(10)).toBe("10,00");
  });
});
