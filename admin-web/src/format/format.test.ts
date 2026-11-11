import { describe, expect, it } from "vitest";
import {
  formatCountdown,
  formatDateTime,
  formatDistance,
  formatScore,
  formatShortDate,
  formatWait,
  severityLabel,
  statusLabel,
} from "./format";

describe("formatScore", () => {
  it("usa coma y dos decimales", () => {
    expect(formatScore(8.7)).toBe("8,70");
  });

  it("conserva los dos decimales en un entero", () => {
    expect(formatScore(10)).toBe("10,00");
  });
});

describe("fechas en hora de Bogotá", () => {
  it("formato corto", () => {
    expect(formatShortDate("2026-10-13T21:05:00Z")).toBe("13 oct");
  });

  it("el día es el de Bogotá, no el de UTC", () => {
    expect(formatShortDate("2026-10-14T03:30:00Z")).toBe("13 oct");
  });

  it("fecha y hora del historial", () => {
    expect(formatDateTime("2026-10-13T21:05:00Z")).toBe("13 oct, 4:05 p. m.");
  });

  it("hora de la mañana y medianoche", () => {
    expect(formatDateTime("2026-10-13T14:00:00Z")).toBe("13 oct, 9:00 a. m.");
    expect(formatDateTime("2026-10-13T05:07:00Z")).toBe("13 oct, 12:07 a. m.");
  });
});

describe("formatDistance", () => {
  it("un decimal con coma y la unidad", () => {
    expect(formatDistance(225.54)).toBe("225,5 m");
  });
});

describe("etiquetas", () => {
  it("estados", () => {
    expect(statusLabel("registrado")).toBe("Registrado");
    expect(statusLabel("evaluado")).toBe("Evaluado");
    expect(statusLabel("priorizado")).toBe("Priorizado");
    expect(statusLabel("reparado")).toBe("Reparado");
  });

  it("severidades", () => {
    expect(severityLabel("baja")).toBe("Baja");
    expect(severityLabel("media")).toBe("Media");
    expect(severityLabel("alta")).toBe("Alta");
  });
});

describe("formatWait", () => {
  it.each([
    [272, "4 min 32 s"],
    [240, "4 min"],
    [32, "32 s"],
    [0.4, "1 s"],
    [-5, "0 s"],
  ])("%d s → %s", (seconds, expected) => {
    expect(formatWait(seconds)).toBe(expected);
  });
});

describe("formatCountdown", () => {
  it.each([
    [272, "4:32"],
    [65, "1:05"],
    [9, "0:09"],
    [0, "0:00"],
  ])("%d s → %s", (seconds, expected) => {
    expect(formatCountdown(seconds)).toBe(expected);
  });
});
