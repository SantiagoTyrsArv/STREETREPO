import { act, render } from "@testing-library/react";
import gsap from "gsap";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockReducedMotion } from "../test/matchMedia";
import { ProximityText } from "./ProximityText";

type Tick = (time: number, deltaMs: number) => void;
let add: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  add = vi.spyOn(gsap.ticker, "add");
  vi.stubGlobal("innerWidth", 800);
  vi.stubGlobal("innerHeight", 600);
  // Cada letra mide 20 px y la palabra empieza en (100, 100).
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (
    this: HTMLElement,
  ) {
    const index = Number(this.dataset.index ?? -1);
    return index >= 0 ? new DOMRect(100 + index * 20, 100, 20, 30) : new DOMRect(100, 100, 180, 30);
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function run(frames = 200) {
  const tick = add.mock.calls.at(-1)?.[0] as Tick;
  act(() => {
    for (let i = 0; i < frames; i++) tick(i / 60, 16);
  });
}

describe("ProximityText", () => {
  it("el lector de pantalla recibe el texto completo una sola vez", () => {
    const { container } = render(
      <ProximityText text="Descargar" by="char" axes={{ wght: [700, 900] }} />,
    );
    expect(container.querySelector(".visually-hidden")?.textContent).toBe("Descargar");
    const parts = container.querySelectorAll("[data-index]");
    expect(parts).toHaveLength(9);
    expect(parts[0]?.closest("[aria-hidden='true']")).not.toBeNull();
  });

  it("con movimiento reducido es texto plano", () => {
    mockReducedMotion(true);
    const { container } = render(
      <ProximityText text="Descargar" by="char" axes={{ wght: [700, 900] }} />,
    );
    expect(container.textContent).toBe("Descargar");
    expect(container.querySelectorAll("[data-index]")).toHaveLength(0);
  });

  it("se engrosa bajo el dedo y vuelve exactamente al reposo al soltarlo", () => {
    const { container } = render(
      <ProximityText text="Descargar" by="char" axes={{ wght: [700, 900], wdth: [100, 115] }} />,
    );
    const first = container.querySelector("[data-index='0']") as HTMLElement;
    const rest = first.style.fontVariationSettings;
    expect(rest).toBe('"wght" 700, "wdth" 100');

    act(() => {
      window.dispatchEvent(
        new PointerEvent("pointerdown", { clientX: 110, clientY: 115, pointerType: "touch" }),
      );
    });
    run();
    expect(Number(/"wght" (\d+)/.exec(first.style.fontVariationSettings)?.[1])).toBeGreaterThan(
      850,
    );

    act(() => {
      window.dispatchEvent(new PointerEvent("pointerup", { pointerType: "touch" }));
    });
    run();
    expect(first.style.fontVariationSettings).toBe(rest);
  });

  it("por palabra parte en palabras", () => {
    const { container } = render(
      <ProximityText text="Una foto y la ubicación" by="word" axes={{ wght: [400, 600] }} />,
    );
    expect(container.querySelectorAll("[data-index]")).toHaveLength(5);
  });
});
