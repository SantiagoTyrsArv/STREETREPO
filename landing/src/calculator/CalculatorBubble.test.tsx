import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CalculatorBubble } from "./CalculatorBubble";

type Callback = (entries: Partial<IntersectionObserverEntry>[]) => void;
let notify: Callback = () => undefined;

class FakeObserver {
  constructor(callback: Callback) {
    notify = callback;
  }
  observe() {}
  disconnect() {}
}

function setupPage() {
  const hero = document.createElement("section");
  hero.id = "apertura";
  const download = document.createElement("section");
  download.id = "descarga";
  document.body.append(hero, download);
  return { hero, download };
}

beforeEach(() => vi.stubGlobal("IntersectionObserver", FakeObserver));
afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

const bubble = () =>
  document.querySelector<HTMLButtonElement>(".calc-bubble__button") as HTMLButtonElement;

describe("CalculatorBubble", () => {
  it("está oculta en la portada y aparece al pasarla", () => {
    const { hero } = setupPage();
    const { container } = render(<CalculatorBubble />);
    const root = container.querySelector(".calc-bubble");
    expect(root).toHaveAttribute("data-visible", "false");
    expect(bubble()).toHaveAttribute("tabindex", "-1");
    act(() =>
      notify([
        {
          target: hero,
          isIntersecting: false,
          boundingClientRect: { top: -2000 } as DOMRectReadOnly,
        },
      ]),
    );
    expect(root).toHaveAttribute("data-visible", "true");
    expect(bubble()).toHaveAttribute("tabindex", "0");
  });

  it("se oculta en la descarga para no tapar su botón", () => {
    const { hero, download } = setupPage();
    const { container } = render(<CalculatorBubble />);
    act(() =>
      notify([
        {
          target: hero,
          isIntersecting: false,
          boundingClientRect: { top: -2000 } as DOMRectReadOnly,
        },
        { target: download, isIntersecting: true },
      ]),
    );
    expect(container.querySelector(".calc-bubble")).toHaveAttribute("data-visible", "false");
  });

  it("abre la calculadora en un panel y Escape la cierra devolviendo el foco", () => {
    const { hero } = setupPage();
    render(<CalculatorBubble />);
    act(() =>
      notify([
        {
          target: hero,
          isIntersecting: false,
          boundingClientRect: { top: -2000 } as DOMRectReadOnly,
        },
      ]),
    );
    expect(screen.queryByRole("dialog")).toBeNull();
    fireEvent.click(bubble());
    const dialog = screen.getByRole("dialog", { name: "Calcula una urgencia." });
    expect(bubble()).toHaveAttribute("aria-expanded", "true");
    expect(within(dialog).getByRole("status")).toHaveTextContent("8,70");
    expect(dialog).toContainElement(document.activeElement as HTMLElement);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(bubble());
  });

  it("el botón de cerrar también cierra", () => {
    const { hero } = setupPage();
    render(<CalculatorBubble />);
    act(() =>
      notify([
        {
          target: hero,
          isIntersecting: false,
          boundingClientRect: { top: -2000 } as DOMRectReadOnly,
        },
      ]),
    );
    fireEvent.click(bubble());
    fireEvent.click(screen.getByRole("button", { name: "Cerrar la calculadora" }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("sin IntersectionObserver queda visible", () => {
    vi.stubGlobal("IntersectionObserver", undefined);
    const { container } = render(<CalculatorBubble />);
    expect(container.querySelector(".calc-bubble")).toHaveAttribute("data-visible", "true");
  });
});
