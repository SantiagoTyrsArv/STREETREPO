import { afterEach, describe, expect, it, vi } from "vitest";
import { mockIntersection } from "../test/intersection";
import { trackVisibility } from "./visibility";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("trackVisibility", () => {
  it("sigue si el elemento está en pantalla", () => {
    const io = mockIntersection();
    const tracker = trackVisibility(document.createElement("div"));
    io.set(false);
    expect(tracker.visible).toBe(false);
    io.set(true);
    expect(tracker.visible).toBe(true);
  });

  it("al detenerse deja de observar", () => {
    const io = mockIntersection();
    const tracker = trackVisibility(document.createElement("div"));
    tracker.stop();
    expect(io.count).toBe(0);
  });

  it("sin IntersectionObserver se considera visible", () => {
    vi.stubGlobal("IntersectionObserver", undefined);
    expect(trackVisibility(document.createElement("div")).visible).toBe(true);
  });
});
