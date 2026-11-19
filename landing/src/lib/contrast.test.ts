import { describe, expect, it } from "vitest";
import { contrastRatio } from "./contrast";

describe("contrastRatio", () => {
  it("da 21:1 entre negro y blanco", () => {
    expect(contrastRatio("#000000", "#FFFFFF")).toBeCloseTo(21, 1);
  });

  it.each([
    ["papel sobre noche", "#F5F3EE", "#0A0E13"],
    ["niebla sobre noche", "#8A94A3", "#0A0E13"],
    ["ámbar sobre noche", "#F5B800", "#0A0E13"],
    ["señal sobre noche", "#4C8DFF", "#0A0E13"],
    ["reparación sobre noche", "#3DD68C", "#0A0E13"],
    ["tinta sobre papel", "#1B2430", "#F5F3EE"],
  ])("cumple WCAG AA (≥ 4,5:1): %s", (_name, fg, bg) => {
    expect(contrastRatio(fg, bg)).toBeGreaterThanOrEqual(4.5);
  });
});
