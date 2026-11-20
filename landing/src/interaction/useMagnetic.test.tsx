import { renderHook } from "@testing-library/react";
import gsap from "gsap";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useMagnetic } from "./useMagnetic";

type Tick = (time: number, deltaMs: number) => void;

function mockFinePointer(matches: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query: string) => ({
      matches: query.includes("pointer: fine") ? matches : false,
      media: query,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    })),
  );
}

let el: HTMLAnchorElement;
let add: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  el = document.createElement("a");
  // Botón de 100 × 40 con el centro en (150, 120).
  el.getBoundingClientRect = () => new DOMRect(100, 100, 100, 40);
  add = vi.spyOn(gsap.ticker, "add");
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function settle() {
  const tick = add.mock.calls.at(-1)?.[0] as Tick;
  for (let i = 0; i < 300; i++) tick(i / 60, 16);
}

function move(clientX: number, clientY: number) {
  window.dispatchEvent(new PointerEvent("pointermove", { clientX, clientY, pointerType: "mouse" }));
}

describe("useMagnetic", () => {
  it("en pantallas táctiles (sin puntero fino) no hace nada", () => {
    mockFinePointer(false);
    renderHook(() => useMagnetic({ current: el }, true));
    expect(add).not.toHaveBeenCalled();
  });

  it("desactivado (movimiento reducido) no hace nada", () => {
    mockFinePointer(true);
    renderHook(() => useMagnetic({ current: el }, false));
    expect(add).not.toHaveBeenCalled();
  });

  it("se acerca al cursor dentro del radio y vuelve al salir", () => {
    mockFinePointer(true);
    renderHook(() => useMagnetic({ current: el }, true));

    move(190, 120); // 40 px a la derecha del centro
    settle();
    expect(el.style.transform).toMatch(/^translate\(4(\.0+)?px(, 0px)?\)$/);

    move(350, 120); // 200 px: fuera del radio
    settle();
    expect(el.style.transform).toMatch(/^translate\(0px(, 0px)?\)$/);
  });

  it("ilumina el punto del botón que está bajo el cursor", () => {
    mockFinePointer(true);
    renderHook(() => useMagnetic({ current: el }, true));
    move(125, 110); // un cuarto del ancho, un cuarto del alto
    expect(el.style.getPropertyValue("--spot-x")).toBe("25%");
    expect(el.style.getPropertyValue("--spot-y")).toBe("25%");
  });

  it("al desmontar deja el botón como estaba", () => {
    mockFinePointer(true);
    const { unmount } = renderHook(() => useMagnetic({ current: el }, true));
    move(190, 120);
    settle();
    unmount();
    expect(el.style.transform).toBe("");
  });
});
