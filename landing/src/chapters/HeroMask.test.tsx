import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { HeroMask } from "./HeroMask";
import { MASK_UNTIL } from "./heroMaskScale";

describe("HeroMask", () => {
  it("es decorativa", () => {
    const { container } = render(<HeroMask progress={0} />);
    expect(container.querySelector(".hero-mask")).toHaveAttribute("aria-hidden", "true");
    expect(container.textContent).toContain("STREET");
  });

  it("desaparece al terminar de atravesar las letras", () => {
    const { container } = render(<HeroMask progress={MASK_UNTIL + 0.01} />);
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

  it("rellena las letras de color al empezar", () => {
    const { container } = render(<HeroMask progress={0} />);
    const fill = container.querySelector(".hero-mask__fill");
    expect(fill?.textContent).toContain("STREET");
    expect(fill?.closest("mask")).toBeNull();
    expect(fill).toHaveAttribute("fill-opacity", "1");
  });

  it("con el zoom el color se desvanece y deja ver la escena", () => {
    const { container } = render(<HeroMask progress={MASK_UNTIL / 2} />);
    const opacity = Number(
      container.querySelector(".hero-mask__fill")?.getAttribute("fill-opacity"),
    );
    expect(opacity).toBeGreaterThan(0);
    expect(opacity).toBeLessThan(1);
  });

  it("el HTML prerenderizado trae las dos disposiciones (sin esperar a JavaScript)", () => {
    // Antes la disposición vertical se elegía al hidratar: en el celular se veía «STREET RE»
    // cortado en una línea hasta que cargaba el JavaScript.
    const html = renderToString(<HeroMask progress={0} />);
    expect(html).toContain("hero-mask__text--landscape");
    expect(html).toContain("hero-mask__text--portrait");
  });

  it("el CSS muestra una sola disposición según la orientación", () => {
    const css = readFileSync(resolve(__dirname, "HeroMask.css"), "utf8");
    expect(css).toMatch(/\.hero-mask__text--portrait\s*\{\s*display:\s*none/);
    const portrait = /@media \(orientation: portrait\)\s*\{([\s\S]*?)\n\}/.exec(css)?.[1] ?? "";
    expect(portrait).toMatch(/\.hero-mask__text--landscape\s*\{\s*display:\s*none/);
    expect(portrait).toMatch(/\.hero-mask__text--portrait\s*\{\s*display:\s*inline/);
  });
});
