import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockReducedMotion } from "../test/matchMedia";

const webgl = vi.hoisted(() => ({ available: true }));
vi.mock("../three/isWebGLAvailable", () => ({ isWebGLAvailable: () => webgl.available }));

import { AmbientBackground } from "./AmbientBackground";

/** Contexto WebGL falso: cualquier método es un espía; compilar y enlazar siempre funciona. */
function fakeGl() {
  const calls = new Map<string, ReturnType<typeof vi.fn>>();
  return new Proxy({} as Record<string, unknown>, {
    get(_, key: string) {
      if (key === "getShaderParameter" || key === "getProgramParameter") return () => true;
      if (key === "canvas") return undefined;
      if (/^[A-Z_0-9]+$/.test(key)) return 1;
      if (!calls.has(key))
        calls.set(
          key,
          vi.fn(() => ({})),
        );
      return calls.get(key);
    },
  });
}

beforeEach(() => {
  webgl.available = true;
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(
    () => fakeGl() as unknown as WebGLRenderingContext,
  );
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      observe(): void {}
      unobserve(): void {}
      disconnect(): void {}
    },
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("AmbientBackground", () => {
  it("sin WebGL no dibuja nada (quedan los degradados CSS)", () => {
    webgl.available = false;
    const { container } = render(<AmbientBackground />);
    expect(container.querySelector("canvas")).toBeNull();
  });

  it("con movimiento reducido no dibuja nada", () => {
    mockReducedMotion(true);
    const { container } = render(<AmbientBackground />);
    expect(container.querySelector("canvas")).toBeNull();
  });

  it("con WebGL monta un lienzo decorativo", () => {
    const { container } = render(<AmbientBackground />);
    const canvas = container.querySelector("canvas");
    expect(canvas).toHaveAttribute("aria-hidden", "true");
  });

  it("si el navegador pierde el contexto, se oculta sin errores", () => {
    const { container } = render(<AmbientBackground />);
    const canvas = container.querySelector("canvas") as HTMLCanvasElement;
    act(() => {
      canvas.dispatchEvent(new Event("webglcontextlost", { cancelable: true }));
    });
    expect(canvas).toHaveClass("ambient--lost");
    act(() => {
      canvas.dispatchEvent(new Event("webglcontextrestored"));
    });
    expect(canvas).not.toHaveClass("ambient--lost");
  });

  it("se apaga si la persona activa «reducir movimiento» con la página abierta", () => {
    const media = mockReducedMotion(false);
    const { container } = render(<AmbientBackground />);
    expect(container.querySelector("canvas")).not.toBeNull();
    act(() => media.set(true));
    expect(container.querySelector("canvas")).toBeNull();
  });
});
