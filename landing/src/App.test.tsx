import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { mockReducedMotion } from "./test/matchMedia";
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
  expect(accents).toEqual([
    "none",
    "amber",
    "amber",
    "signal",
    "signal",
    "signal",
    "repair",
    // Descarga en verde (la solución); el botón sigue ámbar.
    "repair",
  ]);
});

it("las secciones sin video dejan ver el fondo ambiental", () => {
  const { container } = render(<App />);
  const seeThrough = [...container.querySelectorAll('[data-ambient="visible"]')].map(
    (el) => el.className.split(" ")[0],
  );
  expect(seeThrough).toEqual(["reportar", "calc", "panel", "download", "site-footer"]);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

it("la portada empieza enmascarada con el indicador de scroll", () => {
  const { container } = render(<App />);
  expect(container.querySelector(".hero-mask")).not.toBeNull();
  expect(screen.getByText("Desliza")).toBeInTheDocument();
});

it("con movimiento reducido la portada no tiene máscara", () => {
  mockReducedMotion(true);
  const { container } = render(<App />);
  expect(container.querySelector(".hero-mask")).toBeNull();
});
