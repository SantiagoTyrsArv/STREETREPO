import { describe, expect, it } from "vitest";
import { MAX_FRAME_WAIT_MS, shouldStart } from "./playback";

describe("shouldStart", () => {
  it("no empieza antes de entrar al capítulo", () => {
    expect(shouldStart({ triggered: false, ready: true, waitedMs: 0 })).toBe(false);
  });

  it("empieza al entrar si los cuadros están listos", () => {
    expect(shouldStart({ triggered: true, ready: true, waitedMs: 0 })).toBe(true);
  });

  it("espera los cuadros hasta el tope", () => {
    expect(shouldStart({ triggered: true, ready: false, waitedMs: 2499 })).toBe(false);
  });

  it("al llegar al tope empieza aunque falten cuadros", () => {
    expect(MAX_FRAME_WAIT_MS).toBe(2500);
    expect(shouldStart({ triggered: true, ready: false, waitedMs: 2500 })).toBe(true);
  });
});
