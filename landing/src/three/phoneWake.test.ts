import { describe, expect, it } from "vitest";
import { phoneWakeKey } from "./phoneWake";

describe("phoneWakeKey", () => {
  it("fuera de pantalla nunca despierta el lienzo del teléfono", () => {
    expect(phoneWakeKey(false, { active: true, x: 0.3, y: 0.1 })).toBeNull();
  });

  it("en pantalla cambia cuando cambia el puntero", () => {
    const a = phoneWakeKey(true, { active: true, x: 0.3, y: 0.1 });
    const b = phoneWakeKey(true, { active: true, x: 0.4, y: 0.1 });
    expect(a).not.toBeNull();
    expect(a).not.toBe(b);
  });
});
