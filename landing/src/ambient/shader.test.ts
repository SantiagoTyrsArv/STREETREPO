import { describe, expect, it } from "vitest";
import { FRAGMENT_SOURCE } from "./shader";

describe("FRAGMENT_SOURCE", () => {
  it("pide precisión alta donde existe (en celulares mediump es de 16 bits)", () => {
    expect(FRAGMENT_SOURCE).toMatch(
      /#ifdef GL_FRAGMENT_PRECISION_HIGH\s+precision highp float;\s+#else\s+precision mediump float;\s+#endif/,
    );
  });

  it("el brillo del puntero y de la onda respeta la penumbra de la columna de texto", () => {
    expect(FRAGMENT_SOURCE).toMatch(/\(lens \* [\d.]+ \+ ring \* [\d.]+\) \* light/);
  });
});
