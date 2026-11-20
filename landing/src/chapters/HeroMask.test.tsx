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
});
