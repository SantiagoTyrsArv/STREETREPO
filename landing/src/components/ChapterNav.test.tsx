import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { ChapterNav } from "./ChapterNav";
import { pickActive } from "./chapters";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("pickActive", () => {
  it("elige el capítulo que contiene la línea media de la ventana", () => {
    const entries = [
      { id: "a", top: -500, height: 600 },
      { id: "b", top: 100, height: 800 },
    ];
    expect(pickActive(entries, 800)).toBe("b");
    expect(pickActive([], 800)).toBeNull();
  });
});

const CHAPTERS = [
  { id: "uno", label: "Uno" },
  { id: "dos", label: "Dos" },
];

describe("ChapterNav", () => {
  it("tiene un enlace por capítulo, alcanzable con teclado", () => {
    render(<ChapterNav chapters={CHAPTERS} />);
    const nav = screen.getByRole("navigation", { name: "Capítulos" });
    const links = nav.querySelectorAll("a");
    expect([...links].map((a) => a.getAttribute("href"))).toEqual(["#uno", "#dos"]);
    expect(screen.getByRole("link", { name: "Dos" }).tabIndex).not.toBe(-1);
  });

  it("marca el capítulo que se está viendo", async () => {
    vi.stubGlobal("innerHeight", 800);
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (
      this: HTMLElement,
    ) {
      if (this.id === "uno") return new DOMRect(0, -900, 1000, 800);
      if (this.id === "dos") return new DOMRect(0, -100, 1000, 900);
      return new DOMRect();
    });
    render(
      <>
        <section id="uno" />
        <section id="dos" />
        <ChapterNav chapters={CHAPTERS} />
      </>,
    );
    act(() => {
      window.dispatchEvent(new Event("scroll"));
    });
    await waitFor(() =>
      expect(screen.getByRole("link", { name: "Dos" })).toHaveAttribute("aria-current", "true"),
    );
    expect(screen.getByRole("link", { name: "Uno" })).not.toHaveAttribute("aria-current");
  });

  it("cada enlace de la barra lleva a una sección de la página", () => {
    render(<App />);
    const nav = screen.getByRole("navigation", { name: "Capítulos" });
    expect(nav.querySelector('a[href="#prueba"]')).toBeNull();
    for (const a of nav.querySelectorAll("a")) {
      const id = a.getAttribute("href")?.slice(1) ?? "";
      expect(document.getElementById(id)).not.toBeNull();
    }
  });
});
