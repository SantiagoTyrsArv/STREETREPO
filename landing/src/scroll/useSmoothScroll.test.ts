import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SNAP_OPTIONS, useSmoothScroll } from "./useSmoothScroll";

const snapCalls = vi.hoisted(() => ({
  created: [] as unknown[],
  added: [] as [HTMLElement, unknown][],
  destroyed: 0,
}));

vi.mock("lenis", () => ({
  default: class {
    on(): void {}
    raf(): void {}
    scrollTo(): void {}
    destroy(): void {}
    stop(): void {}
    start(): void {}
  },
}));

vi.mock("lenis/snap", () => ({
  default: class {
    constructor(_lenis: unknown, options: unknown) {
      snapCalls.created.push(options);
    }
    addElement(element: HTMLElement, options: unknown) {
      snapCalls.added.push([element, options]);
      return () => undefined;
    }
    destroy() {
      snapCalls.destroyed++;
    }
  },
}));

beforeEach(() => {
  snapCalls.created.length = 0;
  snapCalls.added.length = 0;
  snapCalls.destroyed = 0;
  document.body.innerHTML =
    "<main><section></section><section></section><section></section></main>";
});

afterEach(() => {
  document.body.innerHTML = "";
});

describe("useSmoothScroll", () => {
  it("crea un imán de proximidad con un punto por capítulo", () => {
    renderHook(() => useSmoothScroll(true));
    expect(snapCalls.created).toEqual([SNAP_OPTIONS]);
    expect(SNAP_OPTIONS.type).toBe("proximity");
    expect(snapCalls.added).toHaveLength(3);
    for (const [element, options] of snapCalls.added) {
      expect(element.tagName).toBe("SECTION");
      expect(options).toEqual({ align: "start" });
    }
  });

  it("sin animaciones no hay imán", () => {
    renderHook(() => useSmoothScroll(false));
    expect(snapCalls.created).toHaveLength(0);
  });

  it("al desmontar destruye el imán", () => {
    const { unmount } = renderHook(() => useSmoothScroll(true));
    unmount();
    expect(snapCalls.destroyed).toBe(1);
  });
});
