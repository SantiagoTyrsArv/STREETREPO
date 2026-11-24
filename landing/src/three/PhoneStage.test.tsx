import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockReducedMotion } from "../test/matchMedia";
import { FAN_FROM, fanOpening, PhoneStage, screenIndexForProgress } from "./PhoneStage";

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
    expect(screenIndexForProgress(0.25, 4)).toBe(1);
    expect(screenIndexForProgress(0.4, 4)).toBe(2);
    expect(screenIndexForProgress(0.55, 4)).toBe(3);
    expect(screenIndexForProgress(0.8, 4)).toBe(3);
    expect(screenIndexForProgress(1, 4)).toBe(3);
    expect(screenIndexForProgress(-1, 4)).toBe(0);
  });
});

const FAN = [
  { src: "/media/app/captura-duplicado.webp", alt: "Posible duplicado" },
  { src: "/media/app/captura-confirmar.webp", alt: "Confirmar este daño" },
] as const;

describe("abanico de tres teléfonos", () => {
  it("se abre en el último tercio y queda abierto al final", () => {
    expect(fanOpening(0.5)).toBe(0);
    expect(fanOpening(FAN_FROM)).toBe(0);
    expect(fanOpening(0.8)).toBeGreaterThan(0);
    expect(fanOpening(0.8)).toBeLessThan(1);
    expect(fanOpening(1)).toBe(1);
  });

  it("sin WebGL arma el abanico con las capturas planas al final", () => {
    mockReducedMotion(false);
    render(<PhoneStage progress={1} screens={SCREENS} fan={FAN} fanCaption="Tres teléfonos" />);
    expect(screen.getByRole("img", { name: "Mapa" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Posible duplicado" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Confirmar este daño" })).toBeInTheDocument();
  });

  it("antes del último tercio solo se ve el teléfono principal", () => {
    mockReducedMotion(false);
    render(<PhoneStage progress={0.3} screens={SCREENS} fan={FAN} />);
    expect(screen.queryByRole("img", { name: "Posible duplicado" })).toBeNull();
  });

  it("con movimiento reducido no hay abanico", () => {
    mockReducedMotion(true);
    render(<PhoneStage progress={1} screens={SCREENS} fan={FAN} />);
    expect(screen.queryByRole("img", { name: "Posible duplicado" })).toBeNull();
  });
});
