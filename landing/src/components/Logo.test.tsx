import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Logo } from "./Logo";

describe("Logo", () => {
  it.each(["horizontal", "stacked", "symbol"] as const)(
    "la variante %s se anuncia como «Street Repo»",
    (variant) => {
      render(<Logo variant={variant} />);
      expect(screen.getByRole("img", { name: "Street Repo" })).toBeInTheDocument();
    },
  );

  it("solo la variante de símbolo omite el nombre escrito", () => {
    const { container } = render(<Logo variant="symbol" />);
    expect(container).not.toHaveTextContent("Street Repo");
  });

  it("el tono mono pinta con currentColor", () => {
    const { container } = render(<Logo variant="symbol" tone="mono" />);
    expect(container.querySelector("circle[mask]")).toHaveAttribute("fill", "currentColor");
  });

  it("dos logos en la misma página no comparten la máscara", () => {
    const { container } = render(
      <>
        <Logo variant="symbol" />
        <Logo variant="symbol" />
      </>,
    );
    const ids = [...container.querySelectorAll("mask")].map((m) => m.id);
    expect(new Set(ids).size).toBe(2);
  });
});
