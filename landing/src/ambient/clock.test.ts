import { describe, expect, it } from "vitest";
import { advanceTime, TIME_WRAP } from "./clock";

describe("advanceTime", () => {
  it("suma solo el tiempo de los cuadros dibujados", () => {
    expect(advanceTime(10, 0.016)).toBeCloseTo(10.016);
  });

  it("da la vuelta para que el shader no pierda precisión en celulares", () => {
    expect(advanceTime(TIME_WRAP - 0.01, 0.02)).toBeCloseTo(0.01);
    expect(TIME_WRAP).toBeLessThanOrEqual(1024);
  });
});
