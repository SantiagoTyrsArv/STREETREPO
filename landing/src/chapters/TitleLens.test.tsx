import { render } from "@testing-library/react";
import { useRef } from "react";
import gsap from "gsap";
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

  it("cada palabra se recorta con la máscara de su línea (no se pinta fuera mientras entra)", () => {
    const calls: string[] = [];
    const ctx = new Proxy(
      {},
      {
        get: (_, key: string) =>
          key === "measureText"
            ? () => ({ width: 10, fontBoundingBoxAscent: 8, fontBoundingBoxDescent: 2 })
            : () => {
                calls.push(key);
              },
        set: () => true,
      },
    );
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
      ctx as unknown as CanvasRenderingContext2D,
    );
    const add = vi.spyOn(gsap.ticker, "add");
    const { container } = render(<MaskedScene />);
    expect(container.querySelectorAll(".reveal__line-mask")).toHaveLength(1);
    const tick = add.mock.calls.at(-1)?.[0] as () => void;
    tick();
    const fills = calls.filter((c) => c === "fillText").length;
    const clips = calls.filter((c) => c === "clip").length;
    expect(fills).toBe(2);
    expect(clips).toBe(fills);
  });
});

function MaskedScene() {
  const ref = useRef<HTMLElement>(null);
  return (
    <section ref={ref}>
      <canvas className="frame-sequence__canvas" />
      <h2 className="chapter__title">
        <div className="reveal__line-mask">
          <div className="reveal__line">
            <span className="reveal__word">Calle</span>{" "}
            <span className="reveal__word">reparada.</span>
          </div>
        </div>
      </h2>
      <TitleLens section={ref} />
    </section>
  );
}
