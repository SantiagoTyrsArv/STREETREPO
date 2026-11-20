import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HeroMask } from "./HeroMask";

describe("HeroMask", () => {
  it("es decorativa", () => {
    const { container } = render(<HeroMask progress={0} />);
    expect(container.querySelector(".hero-mask")).toHaveAttribute("aria-hidden", "true");
    expect(container.textContent).toContain("STREET");
  });

  it("desaparece al terminar de atravesar las letras", () => {
    const { container } = render(<HeroMask progress={0.31} />);
    expect(container.querySelector(".hero-mask")).toBeNull();
  });

  it("dibuja encima un contorno tenue de las letras (la escena inicial es casi negra)", () => {
    const { container } = render(<HeroMask progress={0} />);
    const outline = container.querySelector(".hero-mask__outline");
    expect(outline?.textContent).toContain("STREET");
    expect(outline?.closest("mask")).toBeNull();
  });

  it("no fija la capa con will-change: al volver ampliada, se dibuja de nuevo completa", () => {
    // Con will-change: transform el navegador reutiliza el dibujo hecho a la escala del
    // momento: al volver a la portada desde abajo (capa montada ya a ×36) solo existía un trozo
    // pixelado de «STREET REPO».
    const css = readFileSync(resolve(__dirname, "HeroMask.css"), "utf8");
    const rule = /\.hero-mask\s*\{[^}]*\}/.exec(css)?.[0] ?? "";
    expect(rule).not.toMatch(/will-change/);
  });
});
