import { describe, expect, it } from "vitest";
import {
  coverRect,
  frameIndexForProgress,
  nearestLoaded,
  pickResolution,
  preloadOrder,
} from "./math";

describe("frameIndexForProgress", () => {
  it("va del primer al último cuadro", () => {
    expect(frameIndexForProgress(0, 120)).toBe(0);
    expect(frameIndexForProgress(1, 120)).toBe(119);
    expect(frameIndexForProgress(0.5, 120)).toBe(60);
  });

  it("recorta el progreso fuera de 0–1", () => {
    expect(frameIndexForProgress(-0.2, 120)).toBe(0);
    expect(frameIndexForProgress(1.4, 120)).toBe(119);
  });
});

describe("preloadOrder", () => {
  it("carga primero el cuadro 0 y los múltiplos del paso, luego el resto, sin repetir", () => {
    expect(preloadOrder(10, 4)).toEqual([0, 4, 8, 1, 2, 3, 5, 6, 7, 9]);
  });
});

describe("nearestLoaded", () => {
  it("devuelve el cuadro cargado más cercano", () => {
    expect(nearestLoaded(50, new Set([0, 40, 56]))).toBe(56);
  });

  it("ante un empate prefiere el anterior", () => {
    expect(nearestLoaded(50, new Set([45, 55]))).toBe(45);
  });

  it("devuelve null si no hay nada cargado", () => {
    expect(nearestLoaded(5, new Set())).toBeNull();
  });
});

describe("pickResolution", () => {
  it("usa escritorio en pantallas anchas y móvil en verticales o estrechas", () => {
    expect(pickResolution(1440, 900)).toBe("desktop");
    expect(pickResolution(390, 844)).toBe("mobile");
    expect(pickResolution(1024, 1366)).toBe("mobile");
  });
});

describe("coverRect", () => {
  it("recorta la fuente como object-fit: cover", () => {
    expect(coverRect(1920, 1080, 1080, 1080)).toEqual({ sx: 420, sy: 0, sw: 1080, sh: 1080 });
  });

  it("recorta arriba y abajo cuando el destino es más ancho", () => {
    expect(coverRect(1000, 1000, 2000, 1000)).toEqual({ sx: 0, sy: 250, sw: 1000, sh: 500 });
  });
});
