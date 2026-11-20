import { describe, expect, it } from "vitest";
import { falloff } from "./proximity";

describe("falloff", () => {
  it("vale 1 sobre el puntero y 0 desde el radio", () => {
    expect(falloff(0)).toBe(1);
    expect(falloff(140)).toBe(0);
    expect(falloff(200)).toBe(0);
  });

  it("cae suave y sin saltos", () => {
    const mid = falloff(70);
    expect(mid).toBeGreaterThan(0.4);
    expect(mid).toBeLessThan(0.6);
    const values = [0, 35, 70, 105].map((d) => falloff(d));
    for (let i = 1; i < values.length; i++) {
      expect(values[i]).toBeLessThan(values[i - 1] as number);
    }
  });

  it("acepta otro radio", () => {
    expect(falloff(50, 100)).toBeCloseTo(0.5, 5);
  });
});
