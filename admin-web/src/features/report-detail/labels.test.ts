import { describe, expect, it } from "vitest";
import { highwayLabel } from "./labels";

describe("highwayLabel", () => {
  // Todas las etiquetas `highway` que carga la API (propuesta 7, `HIGHWAY_TO_ROAD_CLASS`).
  it.each([
    ["trunk", "troncal"],
    ["trunk_link", "enlace de troncal"],
    ["primary", "primaria"],
    ["primary_link", "enlace de primaria"],
    ["secondary", "secundaria"],
    ["tertiary", "terciaria"],
    ["residential", "residencial"],
    ["unclassified", "sin clasificar"],
    ["service", "de servicio"],
    ["living_street", "de prioridad peatonal"],
  ])("traduce %s", (highway, label) => {
    expect(highwayLabel(highway)).toBe(label);
  });

  it("muestra tal cual una etiqueta no prevista", () => {
    expect(highwayLabel("busway")).toBe("busway");
  });
});
