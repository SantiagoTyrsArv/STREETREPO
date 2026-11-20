import { renderHook } from "@testing-library/react";
import gsap from "gsap";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useDrift } from "./useDrift";

type Tick = (time: number, deltaMs: number) => void;

let el: HTMLDivElement;
let add: ReturnType<typeof vi.spyOn>;
let remove: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  el = document.createElement("div");
  Object.defineProperty(el, "offsetWidth", { value: 1000 });
  Object.defineProperty(el, "offsetHeight", { value: 500 });
  add = vi.spyOn(gsap.ticker, "add");
  remove = vi.spyOn(gsap.ticker, "remove");
});

afterEach(() => {
  vi.restoreAllMocks();
});

function lastTick(): Tick {
  return add.mock.calls.at(-1)?.[0] as Tick;
}

describe("useDrift", () => {
  it("desactivado no se suscribe al reloj de animación", () => {
    renderHook(() => useDrift({ current: el }, { enabled: false }));
    expect(add).not.toHaveBeenCalled();
  });

  it("activo se suscribe y al desmontar se da de baja con la misma función", () => {
    const { unmount } = renderHook(() => useDrift({ current: el }, { enabled: true }));
    expect(add).toHaveBeenCalledTimes(1);
    const tick = lastTick();
    unmount();
    expect(remove).toHaveBeenCalledWith(tick);
  });

  it("sin puntero activo descansa en el centro", () => {
    renderHook(() => useDrift({ current: el }, { enabled: true }));
    const tick = lastTick();
    for (let i = 0; i < 60; i++) tick(i / 60, 16);
    expect(el.style.transform).toBe("translate3d(0px, 0px, 0px)");
  });

  it("sigue al puntero, como mucho el 1,2 % de cada lado (dentro del margen del zoom)", () => {
    renderHook(() => useDrift({ current: el }, { enabled: true }));
    const tick = lastTick();
    window.dispatchEvent(
      new PointerEvent("pointermove", {
        clientX: window.innerWidth,
        clientY: 0,
        pointerType: "mouse",
      }),
    );
    for (let i = 0; i < 300; i++) tick(i / 60, 16);
    // A la derecha y arriba: 1,2 % de 1000 px en x y de 500 px en y.
    expect(el.style.transform).toMatch(/^translate3d\(1[12](\.\d+)?px, -[56](\.\d+)?px, 0px\)$/);
  });

  it("al activar «reducir movimiento» en vivo se detiene y limpia la transformación", () => {
    const { rerender } = renderHook(({ on }) => useDrift({ current: el }, { enabled: on }), {
      initialProps: { on: true },
    });
    const tick = lastTick();
    el.style.transform = "translate3d(3px, 2px, 0)";
    rerender({ on: false });
    expect(remove).toHaveBeenCalledWith(tick);
    expect(el.style.transform).toBe("");
  });
});
