import { render } from "@testing-library/react";
import { useRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TitleLens } from "./TitleLens";

function Scene() {
  const ref = useRef<HTMLElement>(null);
  return (
    <section ref={ref}>
      <canvas className="frame-sequence__canvas" />
      <h2 className="chapter__title">
        <span className="reveal__word">Calle</span> <span className="reveal__word">reparada.</span>
      </h2>
      <TitleLens section={ref} />
    </section>
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("TitleLens", () => {
  it("sin lienzo 2D no hace nada y el título queda normal", () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    const { container } = render(<Scene />);
    expect(container.querySelector(".title-lens")).toBeNull();
    expect(container.querySelector("h2")).not.toHaveClass("chapter__title--lens");
  });

  it("con lienzo 2D dibuja la lupa como decoración y el título sigue siendo el título", () => {
    const ctx = new Proxy({}, { get: () => vi.fn(() => ({ width: 10 })) });
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
      ctx as unknown as CanvasRenderingContext2D,
    );
    const { container, getByRole } = render(<Scene />);
    expect(container.querySelector(".title-lens")).toHaveAttribute("aria-hidden", "true");
    expect(getByRole("heading", { name: "Calle reparada." })).toHaveClass("chapter__title--lens");
  });
});
