import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { COPY } from "../content/copy";
import { mockReducedMotion } from "../test/matchMedia";
import { Panel } from "./Panel";

afterEach(() => {
  vi.unstubAllGlobals();
});

it("muestra la captura real del panel con su texto y la atribución de OSM", () => {
  mockReducedMotion(true);
  render(<Panel />);

  expect(screen.getByRole("heading", { name: COPY.panel.title })).toBeInTheDocument();
  expect(screen.getByRole("img", { name: COPY.panel.alt })).toHaveAttribute(
    "src",
    "/media/panel/priorizacion.webp",
  );
  expect(screen.getByText(/colaboradores de OpenStreetMap/)).toBeInTheDocument();
});
