import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { pointer, startPointerTracking } from "./pointer";

function fire(type: string, init: PointerEventInit & { timeStamp?: number } = {}) {
  window.dispatchEvent(new PointerEvent(type, { bubbles: true, ...init }));
}

let stop: () => void = () => undefined;

beforeEach(() => {
  vi.stubGlobal("innerWidth", 800);
  vi.stubGlobal("innerHeight", 600);
  stop = startPointerTracking();
});

afterEach(() => {
  stop();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("pointer", () => {
  it("sigue al mouse en coordenadas normalizadas", () => {
    fire("pointermove", { clientX: 400, clientY: 300, pointerType: "mouse" });
    expect(pointer).toMatchObject({ x: 0, y: 0, active: true, touch: false });
  });

  it("un toque activa, marca el punto tocado y se suelta al levantar el dedo", () => {
    fire("pointerdown", { clientX: 800, clientY: 0, pointerType: "touch" });
    expect(pointer).toMatchObject({ active: true, touch: true });
    expect(pointer.tap).toMatchObject({ x: 1, y: -1 });

    fire("pointerup", { clientX: 800, clientY: 0, pointerType: "touch" });
    expect(pointer.active).toBe(false);
  });

  it("un toque cancelado por el scroll del navegador también suelta", () => {
    fire("pointerdown", { clientX: 10, clientY: 10, pointerType: "touch" });
    fire("pointercancel", { pointerType: "touch" });
    expect(pointer.active).toBe(false);
  });

  it("el mouse que sale de la ventana deja todo en reposo", () => {
    fire("pointermove", { clientX: 100, clientY: 100, pointerType: "mouse" });
    window.dispatchEvent(new MouseEvent("mouseout", { relatedTarget: null }));
    expect(pointer.active).toBe(false);
  });

  it("mide la rapidez del movimiento", () => {
    fire("pointermove", { clientX: 0, clientY: 300, pointerType: "mouse" });
    fire("pointermove", { clientX: 800, clientY: 300, pointerType: "mouse" });
    expect(pointer.speed).toBeGreaterThan(0);
  });

  it("al detener el seguimiento vuelve al reposo", () => {
    fire("pointerdown", { clientX: 800, clientY: 600, pointerType: "touch" });
    stop();
    expect(pointer).toMatchObject({ x: 0, y: 0, active: false, speed: 0, tap: null });
    stop = startPointerTracking();
  });
});

describe("startPointerTracking", () => {
  it("usa escuchadores pasivos para no frenar el scroll táctil", () => {
    stop();
    const add = vi.spyOn(window, "addEventListener");
    stop = startPointerTracking();
    const pointerCalls = add.mock.calls.filter(([type]) => String(type).startsWith("pointer"));
    expect(pointerCalls.length).toBeGreaterThan(0);
    for (const [, , options] of pointerCalls) {
      expect(options).toMatchObject({ passive: true });
    }
  });

  it("cuenta referencias: solo el último en salir quita los escuchadores", () => {
    const remove = vi.spyOn(window, "removeEventListener");
    const stopSecond = startPointerTracking();
    stopSecond();
    expect(remove).not.toHaveBeenCalled();

    fire("pointermove", { clientX: 800, clientY: 300, pointerType: "mouse" });
    expect(pointer.x).toBe(1);

    stop();
    expect(remove).toHaveBeenCalled();
    stop = startPointerTracking();
  });
});
