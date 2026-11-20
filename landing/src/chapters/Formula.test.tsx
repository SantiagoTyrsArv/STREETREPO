import { render } from "@testing-library/react";
import gsap from "gsap";
import { afterEach, describe, expect, it, vi } from "vitest";
import { COPY } from "../content/copy";
import { Formula } from "./Formula";

afterEach(() => {
  vi.restoreAllMocks();
});

const scrambles = (spy: ReturnType<typeof vi.spyOn>) =>
  spy.mock.calls.filter((call: unknown[]) => (call[1] as { scrambleText?: unknown })?.scrambleText);

describe("Formula", () => {
  it("con movimiento reducido es la fórmula plana, sin contorno", () => {
    const { container } = render(<Formula progress={1} still />);
    const equation = container.querySelector(".formula__equation") as HTMLElement;
    expect(equation.textContent).toBe(COPY.formula);
    expect(equation).not.toHaveClass("formula__equation--stroke");
  });

  it("el lector de pantalla lee la fórmula completa y no el descifrado", () => {
    const { container } = render(<Formula progress={0} still={false} />);
    const equation = container.querySelector(".formula__equation") as HTMLElement;
    expect(equation.querySelector(".visually-hidden")?.textContent).toBe(COPY.formula);
    expect(equation.querySelector("[aria-hidden='true']")).not.toBeNull();
  });

  it("se descifra una sola vez al entrar y termina en la fórmula", () => {
    const to = vi.spyOn(gsap, "to");
    const { rerender } = render(<Formula progress={0.1} still={false} />);
    expect(scrambles(to)).toHaveLength(0);

    rerender(<Formula progress={0.45} still={false} />);
    rerender(<Formula progress={0.6} still={false} />);
    const calls = scrambles(to);
    expect(calls).toHaveLength(1);
    const vars = calls[0]?.[1] as { scrambleText: { text: string } };
    expect(vars.scrambleText.text).toBe(COPY.formula);
  });
});
