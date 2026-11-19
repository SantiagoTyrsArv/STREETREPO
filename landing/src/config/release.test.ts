import { describe, expect, it } from "vitest";
import { formatSize, RELEASE } from "./release";

describe("formatSize", () => {
  it("expresa los bytes en MB con coma decimal", () => {
    expect(formatSize(25_480_000)).toBe("24,3 MB");
    expect(formatSize(900_000)).toBe("0,9 MB");
  });
});

describe("RELEASE", () => {
  it("está vacío mientras la app esté en pruebas", () => {
    expect(RELEASE).toBeNull();
  });
});
