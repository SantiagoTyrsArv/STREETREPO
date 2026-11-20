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
});
