import { renderHook } from "@testing-library/react";
import gsap from "gsap";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useTilt } from "./useTilt";

type Tick = (time: number, deltaMs: number) => void;

let el: HTMLDivElement;
let add: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  el = document.createElement("div");
  add = vi.spyOn(gsap.ticker, "add");
});

afterEach(() => {
  vi.restoreAllMocks();
});

function settle() {
  const tick = add.mock.calls.at(-1)?.[0] as Tick;
  for (let i = 0; i < 300; i++) tick(i / 60, 16);
}

describe("useTilt", () => {
  it("desactivado no se suscribe", () => {
    renderHook(() => useTilt({ current: el }, { enabled: false }));
    expect(add).not.toHaveBeenCalled();
  });

  it("sin puntero activo queda de frente", () => {
    renderHook(() => useTilt({ current: el }, { enabled: true }));
    settle();
    expect(el.style.transform).toBe("perspective(1200px) rotateX(0deg) rotateY(0deg)");
  });

  it("se inclina hacia el puntero, como mucho 4°", () => {
    renderHook(() => useTilt({ current: el }, { enabled: true }));
    window.dispatchEvent(
      new PointerEvent("pointermove", {
        clientX: window.innerWidth,
        clientY: 0,
        pointerType: "mouse",
      }),
    );
    settle();
    expect(el.style.transform).toMatch(/rotateX\(4(\.0+)?deg\) rotateY\(4(\.0+)?deg\)$/);
  });

  it("al soltar el dedo vuelve de frente", () => {
    renderHook(() => useTilt({ current: el }, { enabled: true }));
    window.dispatchEvent(
      new PointerEvent("pointerdown", { clientX: 0, clientY: 0, pointerType: "touch" }),
    );
    settle();
    window.dispatchEvent(new PointerEvent("pointerup", { pointerType: "touch" }));
    settle();
    expect(el.style.transform).toBe("perspective(1200px) rotateX(0deg) rotateY(0deg)");
  });
});
