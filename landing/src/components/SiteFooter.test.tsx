import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { SiteFooter } from "./SiteFooter";

it("identifica el proyecto de grado y avisa de los medios generados con IA", () => {
  render(<SiteFooter />);

  const footer = screen.getByRole("contentinfo");
  expect(footer).toHaveTextContent(/Universidad Cooperativa de Colombia, campus Pasto/);
  expect(footer).toHaveTextContent("Imágenes y videos ilustrativos generados con IA");
  expect(footer).toHaveTextContent(String(new Date().getFullYear()));
});
