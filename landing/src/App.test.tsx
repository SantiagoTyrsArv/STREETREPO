import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { App } from "./App";

it("tiene una región principal", () => {
  render(<App />);
  expect(screen.getByRole("main")).toBeInTheDocument();
});

it("cada sección declara el acento que tiñe el fondo ambiental", () => {
  render(<App />);
  const sections = screen.getByRole("main").querySelectorAll("section");
  expect(sections.length).toBeGreaterThan(0);
  const accents = [...sections].map((s) => s.getAttribute("data-accent"));
  expect(accents).toEqual(["none", "amber", "amber", "signal", "signal", "repair", "amber"]);
});

it("las secciones sin video dejan ver el fondo ambiental", () => {
  const { container } = render(<App />);
  const seeThrough = [...container.querySelectorAll('[data-ambient="visible"]')].map(
    (el) => el.className.split(" ")[0],
  );
  expect(seeThrough).toEqual(["reportar", "panel", "download", "site-footer"]);
});
