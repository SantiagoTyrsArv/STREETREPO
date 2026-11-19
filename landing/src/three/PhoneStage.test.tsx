import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockReducedMotion } from "../test/matchMedia";
import { PhoneStage, screenIndexForProgress } from "./PhoneStage";

vi.mock("./isWebGLAvailable", () => ({ isWebGLAvailable: vi.fn(() => false) }));

const SCREENS = [
  { src: "/media/app/captura-foto.webp", alt: "Foto y ubicación" },
  { src: "/media/app/captura-severidad.webp", alt: "Severidad" },
  { src: "/media/app/captura-enviado.webp", alt: "Reporte enviado" },
  { src: "/media/app/captura-mapa.webp", alt: "Mapa" },
] as const;

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("PhoneStage sin WebGL", () => {
  it("muestra la captura que toca como imagen y no monta el lienzo 3D", () => {
    mockReducedMotion(false);
    const { container } = render(<PhoneStage progress={0} screens={SCREENS} />);

    expect(screen.getByRole("img", { name: "Foto y ubicación" })).toHaveAttribute(
      "src",
      "/media/app/captura-foto.webp",
    );
    expect(container.querySelector("canvas")).toBeNull();
  });

  it("cambia de captura según el progreso", () => {
    mockReducedMotion(false);
    render(<PhoneStage progress={0.95} screens={SCREENS} />);

    expect(screen.getByRole("img", { name: "Mapa" })).toBeInTheDocument();
  });
});

describe("PhoneStage con movimiento reducido", () => {
  it("muestra la primera captura fija", () => {
    mockReducedMotion(true);
    const { container } = render(<PhoneStage progress={0.95} screens={SCREENS} />);

    expect(screen.getByRole("img", { name: "Foto y ubicación" })).toBeInTheDocument();
    expect(container.querySelector("canvas")).toBeNull();
  });
});

describe("screenIndexForProgress", () => {
  it("reparte las capturas en tramos iguales del recorrido", () => {
    expect(screenIndexForProgress(0, 4)).toBe(0);
    expect(screenIndexForProgress(0.35, 4)).toBe(1);
    expect(screenIndexForProgress(0.31, 4)).toBe(1);
    expect(screenIndexForProgress(0.55, 4)).toBe(2);
    expect(screenIndexForProgress(0.8, 4)).toBe(3);
    expect(screenIndexForProgress(1, 4)).toBe(3);
    expect(screenIndexForProgress(-1, 4)).toBe(0);
  });
});
