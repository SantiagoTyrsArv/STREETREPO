import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { App } from "../App";

it("el primer elemento enfocable de la página salta a la descarga", () => {
  const { container } = render(<App />);

  const first = container.querySelector<HTMLElement>("a[href], button, [tabindex='0']");
  expect(first).toBe(screen.getByRole("link", { name: "Saltar a la descarga" }));
  expect(first).toHaveAttribute("href", "#descarga");
});
