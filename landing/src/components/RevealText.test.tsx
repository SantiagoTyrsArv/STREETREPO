import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RevealText } from "./RevealText";

const TITLE = "Un modelo transparente decide el orden.";

describe("RevealText por líneas", () => {
  it("el título conserva un solo nombre accesible con el texto completo", () => {
    const { container } = render(
      <RevealText as="h2" text={TITLE} progress={0.5} from={0} to={1} />,
    );
    expect(screen.getByRole("heading", { name: TITLE })).toBeInTheDocument();
    const lines = container.querySelectorAll(".reveal__line");
    expect(lines.length).toBeGreaterThan(0);
    expect(lines[0]?.getAttribute("aria-hidden")).toBe("true");
  });

  it("antes del tramo las líneas esperan bajo la máscara y al final están en su sitio", () => {
    const { container, rerender } = render(
      <RevealText as="h2" text={TITLE} progress={0} from={0.2} to={0.4} />,
    );
    const line = container.querySelector(".reveal__line") as HTMLElement;
    expect(line.style.transform).toMatch(/translateY\(1\d\d%\)/);

    rerender(<RevealText as="h2" text={TITLE} progress={0.4} from={0.2} to={0.4} />);
    expect(line.style.transform).toMatch(/translateY\(0%\)/);
  });

  it("sin animación es texto plano", () => {
    const { container } = render(
      <RevealText as="h2" text={TITLE} progress={0} from={0} to={1} still />,
    );
    expect(container.querySelector(".reveal__line")).toBeNull();
    expect(container.textContent).toBe(TITLE);
  });

  it("por palabras mantiene el comportamiento anterior", () => {
    const { container } = render(
      <RevealText text="Dos palabras" progress={1} from={0} to={1} split="words" />,
    );
    expect(container.querySelectorAll(".reveal__word")).toHaveLength(2);
    expect(container.querySelector(".reveal__line")).toBeNull();
  });
});
